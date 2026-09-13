#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
"""Tests for pr-comments-inline.

Placement is the whole problem, so these drive it directly: --from-json supplies
normalized threads, bypassing GitHub, and the assertions are on the resulting
working-tree files.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "python" / "pr-comments-inline"

GO_SOURCE = """\
package main

import "context"

func run() error {
\tctx := context.Background()
\tif err := do(ctx); err != nil {
\t\treturn err
\t}
\treturn nil
}
"""

PY_SOURCE = """\
#!/usr/bin/env python3

def run():
    return 1
"""


def thread(
    *,
    n: int = 1,
    path: str = "sample.go",
    line: int | None = 7,
    side: str = "RIGHT",
    anchor: str = "\tif err := do(ctx); err != nil {",
    comments: list[tuple[str, str]] | None = None,
    resolved: bool = False,
) -> dict:
    """A normalized thread, as the fetch step would produce it."""
    return {
        "path": path,
        "line": line,
        "side": side,
        "isResolved": resolved,
        "diffHunk": "@@ -5,4 +5,5 @@ func run() error {\n" + "+" + anchor,
        "url": f"https://github.com/o/r/pull/1#discussion_r{n}",
        "comments": [
            {"author": a, "body": b} for a, b in (comments or [("bergundy", "handle it")])
        ],
    }


def run_tool(tmp_path: Path, threads: list[dict], *args: str) -> subprocess.CompletedProcess:
    threads_file = tmp_path / "threads.json"
    threads_file.write_text(json.dumps(threads))
    return subprocess.run(
        [str(SCRIPT_PATH), "--from-json", str(threads_file), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "sample.go").write_text(GO_SOURCE)
    (tmp_path / "script.py").write_text(PY_SOURCE)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=tmp_path,
        check=True,
    )
    return tmp_path


def test_a_thread_is_written_above_its_line_at_that_lines_indentation(repo: Path):
    result = run_tool(repo, [thread()])
    assert result.returncode == 0, result.stderr
    assert (repo / "sample.go").read_text() == GO_SOURCE.replace(
        "\tif err := do(ctx); err != nil {",
        "\t// ⬇️ [1] bergundy\n"
        "\t// ⬇️ handle it\n"
        "\t// ⬇️ https://github.com/o/r/pull/1#discussion_r1\n"
        "\tif err := do(ctx); err != nil {",
    )


def test_replies_are_kept_in_one_block_separated_by_a_bare_marker(repo: Path):
    threads = [thread(comments=[("bergundy", "handle it"), ("dandavison", "will do")])]
    assert run_tool(repo, threads).returncode == 0
    assert (
        "\t// ⬇️ [1] bergundy\n"
        "\t// ⬇️ handle it\n"
        "\t// ⬇️\n"
        "\t// ⬇️ dandavison\n"
        "\t// ⬇️ will do\n"
    ) in (repo / "sample.go").read_text()


def test_the_comment_prefix_follows_the_files_language(repo: Path):
    threads = [thread(path="script.py", line=4, anchor="    return 1")]
    assert run_tool(repo, threads).returncode == 0
    assert "    # ⬇️ [1] bergundy\n    # ⬇️ handle it\n    return 1" in (
        repo / "script.py"
    ).read_text()


def test_a_thread_whose_line_no_longer_matches_goes_to_a_header_block(repo: Path):
    threads = [thread(anchor="\tthis line is not in the file")]
    assert run_tool(repo, threads).returncode == 0
    text = (repo / "sample.go").read_text()
    assert text.startswith(
        "// ⬇️ [1] bergundy · unplaced (was sample.go:7)\n// ⬇️ handle it\n"
    )
    assert "⬇️" not in text.split("package main")[1]


def test_a_left_side_thread_is_unplaceable_in_the_working_tree(repo: Path):
    threads = [thread(side="LEFT")]
    assert run_tool(repo, threads).returncode == 0
    assert (repo / "sample.go").read_text().startswith("// ⬇️ [1] bergundy · unplaced")


def test_a_header_block_goes_below_a_shebang(repo: Path):
    threads = [thread(path="script.py", line=None)]
    assert run_tool(repo, threads).returncode == 0
    assert (repo / "script.py").read_text().startswith(
        "#!/usr/bin/env python3\n# ⬇️ [1] bergundy · unplaced"
    )


def test_resolved_threads_are_skipped_unless_asked_for(repo: Path):
    assert run_tool(repo, [thread(resolved=True)]).returncode == 0
    assert "⬇️" not in (repo / "sample.go").read_text()
    assert run_tool(repo, [thread(resolved=True)], "--resolved").returncode == 0
    assert "· resolved" in (repo / "sample.go").read_text()


def test_long_bodies_are_wrapped_and_every_line_carries_the_marker(repo: Path):
    body = "the retry loop spins forever here because the error is swallowed " * 3
    assert run_tool(repo, [thread(comments=[("bergundy", body)])]).returncode == 0
    block = [
        line
        for line in (repo / "sample.go").read_text().splitlines()
        if "⬇️" in line
    ]
    assert len(block) > 4
    assert all(line.lstrip().startswith("// ⬇️") for line in block)
    assert all(len(line.expandtabs(4)) <= 88 for line in block)


def test_remove_restores_the_file_exactly(repo: Path):
    assert run_tool(repo, [thread()]).returncode == 0
    assert subprocess.run(
        [str(SCRIPT_PATH), "--remove"], cwd=repo, capture_output=True, timeout=60
    ).returncode == 0
    assert (repo / "sample.go").read_text() == GO_SOURCE


def test_running_twice_is_the_same_as_running_once(repo: Path):
    assert run_tool(repo, [thread()]).returncode == 0
    once = (repo / "sample.go").read_text()
    assert run_tool(repo, [thread()]).returncode == 0
    assert (repo / "sample.go").read_text() == once


def test_a_dirty_working_tree_is_refused(repo: Path):
    (repo / "sample.go").write_text(GO_SOURCE + "// edited\n")
    result = run_tool(repo, [thread()])
    assert result.returncode != 0
    assert "⬇️" not in (repo / "sample.go").read_text()


def test_a_file_with_no_known_comment_syntax_is_reported_not_written(repo: Path):
    (repo / "data.bin").write_bytes(b"\x00binary\n")
    threads = [thread(path="data.bin", line=1, anchor="\x00binary")]
    result = run_tool(repo, threads, "--force")
    assert "data.bin" in result.stderr
    assert (repo / "data.bin").read_bytes() == b"\x00binary\n"
