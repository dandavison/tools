#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
"""Tests for agent-run, using fake claude and codex executables."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

TOOLS = Path(__file__).parent.parent
SCRIPT_PATH = TOOLS / "python" / "agent-run"

CONFIG = """
[accounts.personal]
CLAUDE_CONFIG_DIR = "/tmp/claude-personal"

[[models]]
name = "opus"
cli = "claude"
model = "claude-opus-5-5"

[[models]]
name = "luna"
cli = "codex"
model = "gpt-6-luna"
openrouter = "openai/gpt-6-luna"
"""

OPENROUTER_MODELS = {
    "data": [
        {
            "id": "openai/gpt-6-luna",
            "pricing": {
                "prompt": "0.000001",
                "completion": "0.000002",
                "input_cache_read": "0",
                "input_cache_write": "0",
            },
        }
    ]
}

CLAUDE_EVENTS = [
    {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]},
    },
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "answer"}]}},
    {"type": "result", "subtype": "success", "num_turns": 2, "total_cost_usd": 0.0123},
]

CODEX_EVENTS = [
    {"type": "item.started", "item": {"type": "command_execution"}},
    {"type": "item.completed", "item": {"type": "agent_message", "text": "answer"}},
    {
        "type": "turn.completed",
        "usage": {
            "input_tokens": 1000,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 500,
        },
    },
]


def fake_cli(path: Path, events: list[dict]) -> None:
    """Record argv and the CLAUDE_CONFIG_DIR env var, then emit canned events."""
    lines = "\n".join(json.dumps(e) for e in events)
    path.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$@" > "{path}.argv"\n'
        f'echo "${{CLAUDE_CONFIG_DIR:-}}" > "{path}.env"\n'
        f"cat <<'EOF'\n{lines}\nEOF\n"
    )
    path.chmod(0o755)


@pytest.fixture
def home(tmp_path: Path) -> Path:
    (tmp_path / "agent-models.toml").write_text(CONFIG)
    (tmp_path / "openrouter-models.json").write_text(json.dumps(OPENROUTER_MODELS))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_cli(bin_dir / "claude", CLAUDE_EVENTS)
    fake_cli(bin_dir / "codex", CODEX_EVENTS)
    (bin_dir / "agent-pick").symlink_to(TOOLS / "python" / "agent-pick")
    return tmp_path


def run(
    home: Path, *args: str, stdin: str = "", env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    base_env = {k: v for k, v in os.environ.items() if k != "AGENT_MODEL"}
    return subprocess.run(
        [str(SCRIPT_PATH), *args],
        input=stdin,
        capture_output=True,
        check=False,
        text=True,
        env={
            **base_env,
            "PATH": f"{home / 'bin'}:{os.environ['PATH']}",
            "AGENT_MODELS": str(home / "agent-models.toml"),
            "AGENT_PRICES": str(home / "openrouter-models.json"),
            **(env or {}),
        },
    )


def prompt_sent_to(home: Path, cli: str) -> str:
    return (home / "bin" / f"{cli}.argv").read_text().splitlines()[-1]


@pytest.fixture
def script(home: Path) -> Path:
    path = home / "standup"
    path.write_text("#!/usr/bin/env -S agent-run -m opus\nSummarise.\n")
    return path


def test_stdin_prompt_answer_on_stdout_progress_on_stderr(home: Path) -> None:
    result = run(home, "-m", "opus", stdin="hello")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "answer\n"
    assert "Bash" in result.stderr
    assert "$0.0123" in result.stderr
    assert prompt_sent_to(home, "claude") == "hello"


def test_script_file_strips_shebang_and_appends_args_and_stdin(
    home: Path, script: Path
) -> None:
    result = run(home, "-m", "opus", str(script), "a1", "a2", stdin="data")
    assert result.returncode == 0, result.stderr
    argv = (home / "bin" / "claude.argv").read_text()
    assert "#!" not in argv
    assert "Summarise." in argv
    assert "a1 a2" in argv
    assert "data" in argv


def test_agent_model_env_overrides_m(home: Path, script: Path) -> None:
    result = run(home, "-m", "opus", str(script), env={"AGENT_MODEL": "luna"})
    assert result.returncode == 0, result.stderr
    assert (home / "bin" / "codex.argv").exists()
    assert not (home / "bin" / "claude.argv").exists()


def test_no_model_without_terminal_fails(home: Path) -> None:
    result = run(home, stdin="hello")
    assert result.returncode != 0
    assert "AGENT_MODEL" in result.stderr


def test_codex_answer_on_stdout_cost_on_stderr(home: Path) -> None:
    result = run(home, "-m", "luna", stdin="hello")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "answer\n"
    assert "command_execution" in result.stderr
    assert "$0.002" in result.stderr


def test_personal_sets_account_env(home: Path) -> None:
    result = run(home, "--personal", "-m", "opus", stdin="hello")
    assert result.returncode == 0, result.stderr
    assert (home / "bin" / "claude.env").read_text().strip() == "/tmp/claude-personal"
