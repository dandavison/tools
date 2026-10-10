#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
"""Tests for agent-pick."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "python" / "agent-pick"

CONFIG = """
[accounts.personal]
CLAUDE_CONFIG_DIR = "~/.claude-personal"
CODEX_HOME = "/tmp/codex-personal"

[[models]]
name = "opus"
cli = "claude"
model = "claude-opus-5-5"

[[models]]
name = "luna"
cli = "codex"
model = "gpt-6-luna"
openrouter = "openai/gpt-6-luna"

[[models]]
name = "qwen-local"
cli = "pi"
model = "mlx/qwen"
health = "http://127.0.0.1:1/v1/models"
"""


OPENROUTER_MODELS = {
    "data": [
        {
            "id": "openai/gpt-6-luna",
            "pricing": {
                "prompt": "0.0000001",
                "completion": "0.0000005",
                "input_cache_read": "0.00000001",
                "input_cache_write": "0.000000125",
            },
        }
    ]
}


@pytest.fixture
def config(tmp_path: Path) -> Path:
    path = tmp_path / "agent-models.toml"
    path.write_text(CONFIG)
    (tmp_path / "openrouter-models.json").write_text(json.dumps(OPENROUTER_MODELS))
    return path


def run(config: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT_PATH), *args],
        capture_output=True,
        check=False,
        text=True,
        env={
            **os.environ,
            "AGENT_MODELS": str(config),
            "AGENT_PRICES": str(config.parent / "openrouter-models.json"),
        },
    )


def test_pick_by_name(config: Path) -> None:
    result = run(config, "luna")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "name": "luna",
        "cli": "codex",
        "model": "gpt-6-luna",
        "env": {},
        "price": {
            "input": 0.10,
            "cached_input": 0.01,
            "cache_write": 0.125,
            "output": 0.50,
        },
    }


def test_price_is_null_without_openrouter_id(config: Path) -> None:
    result = run(config, "opus")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["price"] is None


def test_personal_sets_account_env(config: Path) -> None:
    result = run(config, "--personal", "opus")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["env"] == {
        "CLAUDE_CONFIG_DIR": str(Path("~/.claude-personal").expanduser()),
        "CODEX_HOME": "/tmp/codex-personal",
    }


def test_list_excludes_unhealthy_local_model(config: Path) -> None:
    result = run(config, "--list")
    assert result.returncode == 0, result.stderr
    assert [line.split()[0] for line in result.stdout.splitlines()] == ["opus", "luna"]


def test_unhealthy_local_model_by_name_fails(config: Path) -> None:
    result = run(config, "qwen-local")
    assert result.returncode != 0
    assert "qwen-local" in result.stderr


def test_unknown_name_fails(config: Path) -> None:
    result = run(config, "nope")
    assert result.returncode != 0
    assert "nope" in result.stderr


def test_missing_price_cache_fails(config: Path) -> None:
    (config.parent / "openrouter-models.json").unlink()
    result = run(config, "luna")
    assert result.returncode != 0
    assert "agent-prices-refresh" in result.stderr
