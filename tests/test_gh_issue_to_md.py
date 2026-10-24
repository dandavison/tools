#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
"""Tests for gh-issue-to-md, run against a fake `gh` that serves two pages of comments."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "bash" / "gh-issue-to-md"

ISSUE = {"title": "Log", "body": "", "created_at": "2026-01-01T00:00:00Z"}
PAGES = [
    [
        {"user": {"login": "u"}, "created_at": "t1", "body": "# 2026-01-01 a\nx"},
        {"user": {"login": "u"}, "created_at": "t2", "body": "no heading"},
    ],
    [
        {"user": {"login": "u"}, "created_at": "t3", "body": "# 2026-01-02 b\ny"},
        {"user": {"login": "u"}, "created_at": "t4", "body": "# 2026-01-03 c\r\nz"},
    ],
]


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    gh = tmp_path / "gh"
    gh.write_text(
        "#!/bin/bash\n"
        'if [[ "$2" == */comments ]]; then\n'
        f"  echo '{json.dumps(PAGES[0])}'\n"
        f"  echo '{json.dumps(PAGES[1])}'\n"
        "else\n"
        f"  echo '{json.dumps(ISSUE)}'\n"
        "fi\n"
    )
    gh.chmod(0o755)
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}


def comment_times(env: dict[str, str], *args: str) -> list[str]:
    result = subprocess.run(
        [str(SCRIPT_PATH), *args, "1"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return re.findall(r"^### @u on (\S+)$", result.stdout, re.MULTILINE)


def test_all_comments_in_order(env: dict[str, str]):
    assert comment_times(env) == ["t1", "t2", "t3", "t4"]


def test_reverse(env: dict[str, str]):
    assert comment_times(env, "-r") == ["t4", "t3", "t2", "t1"]


def test_last(env: dict[str, str]):
    assert comment_times(env, "--last", "2") == ["t3", "t4"]


def test_last_reverse(env: dict[str, str]):
    assert comment_times(env, "--last", "2", "--reverse") == ["t4", "t3"]


def test_gte(env: dict[str, str]):
    assert comment_times(env, "--gte", "2026-01-02") == ["t3", "t4"]


def test_gt(env: dict[str, str]):
    assert comment_times(env, "--gt", "2026-01-02 b") == ["t4"]


def test_lte(env: dict[str, str]):
    assert comment_times(env, "--lte", "2026-01-02 b") == ["t1", "t3"]


def test_lt(env: dict[str, str]):
    assert comment_times(env, "--lt", "2026-01-02") == ["t1"]


def test_range_with_last(env: dict[str, str]):
    assert comment_times(
        env, "--gt", "2026-01-01", "--lt", "2026-01-04", "--last", "1"
    ) == ["t4"]


def test_no_matching_comments_omits_comments_section(env: dict[str, str]):
    result = subprocess.run(
        [str(SCRIPT_PATH), "--gt", "2027", "1"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "## Comments" not in result.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
