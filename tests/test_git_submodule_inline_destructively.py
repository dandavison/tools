#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///

from __future__ import annotations

import os
import subprocess
from pathlib import Path

TOOL = Path(__file__).parent.parent / "python" / "git-submodule-inline-destructively"


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"GIT_PAGER": "cat"}
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        check=check,
        capture_output=True,
        text=True,
    )


def init_repo(path: Path) -> None:
    path.mkdir()
    git(path, "init", "-b", "main")
    git(path, "config", "user.name", "Test User")
    git(path, "config", "user.email", "test@example.com")


def commit_file(repo: Path, path: str, contents: str, message: str) -> str:
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(contents)
    git(repo, "add", path)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def add_submodule(parent: Path, source: Path, path: str) -> None:
    git(
        parent,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(source),
        path,
    )


def run_tool(parent: Path, path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(TOOL), path],
        cwd=parent,
        env=os.environ | {"GIT_PAGER": "cat"},
        capture_output=True,
        text=True,
    )


def test_inlines_files_and_submodule_history(tmp_path: Path) -> None:
    submodule = tmp_path / "source"
    init_repo(submodule)
    first = commit_file(submodule, "data.txt", "one\n", "sub: add data")
    second = commit_file(submodule, "data.txt", "two\n", "sub: update data")

    parent = tmp_path / "parent"
    init_repo(parent)
    commit_file(parent, "README.md", "parent\n", "parent: initial")
    add_submodule(parent, submodule, "vendor/lib")
    git(parent / "vendor/lib", "checkout", first)
    git(parent, "add", ".gitmodules", "vendor/lib")
    git(parent, "commit", "-m", "parent: add submodule")
    git(parent / "vendor/lib", "checkout", second)
    git(parent, "add", "vendor/lib")
    git(parent, "commit", "-m", "parent: update submodule")

    result = run_tool(parent, "vendor/lib")

    assert result.returncode == 0, result.stderr
    assert (parent / "vendor/lib/data.txt").read_text() == "two\n"
    assert not (parent / ".gitmodules").exists()
    assert not (parent / ".git/modules/vendor/lib").exists()
    assert (
        git(
            parent,
            "config",
            "--get-regexp",
            r"^submodule\.vendor/lib\.",
            check=False,
        ).returncode
        == 1
    )
    assert "160000 commit" not in git(parent, "ls-tree", "-r", "HEAD").stdout
    assert git(
        parent, "log", "--format=%s", "--", "vendor/lib/data.txt"
    ).stdout.splitlines() == [
        "sub: update data",
        "sub: add data",
    ]
    assert git(parent, "log", "--first-parent", "--format=%s").stdout.splitlines() == [
        "parent: update submodule",
        "parent: add submodule",
        "parent: initial",
    ]


def test_preserves_other_submodule_configuration(tmp_path: Path) -> None:
    inline_source = tmp_path / "inline-source"
    init_repo(inline_source)
    commit_file(inline_source, "inline.txt", "inline\n", "add inline file")
    kept_source = tmp_path / "kept-source"
    init_repo(kept_source)
    commit_file(kept_source, "kept.txt", "kept\n", "add kept file")

    parent = tmp_path / "parent"
    init_repo(parent)
    commit_file(parent, "README.md", "parent\n", "parent: initial")
    add_submodule(parent, inline_source, "nested/inline")
    add_submodule(parent, kept_source, "kept")
    git(parent, "commit", "-am", "parent: add submodules")

    result = run_tool(parent, "nested/inline")

    assert result.returncode == 0, result.stderr
    assert (parent / "nested/inline/inline.txt").read_text() == "inline\n"
    assert (
        git(
            parent, "config", "-f", ".gitmodules", "--get", "submodule.kept.path"
        ).stdout.strip()
        == "kept"
    )
    assert (
        git(
            parent,
            "config",
            "-f",
            ".gitmodules",
            "--get",
            "submodule.nested/inline.path",
            check=False,
        ).returncode
        == 1
    )
    assert git(parent, "ls-tree", "HEAD", "kept").stdout.startswith("160000 commit")
    assert git(parent, "ls-tree", "HEAD", "nested/inline").stdout.startswith(
        "040000 tree"
    )


def test_refuses_dirty_parent_without_changing_head(tmp_path: Path) -> None:
    submodule = tmp_path / "source"
    init_repo(submodule)
    commit_file(submodule, "data.txt", "one\n", "sub: add data")
    parent = tmp_path / "parent"
    init_repo(parent)
    commit_file(parent, "README.md", "parent\n", "parent: initial")
    add_submodule(parent, submodule, "vendor/lib")
    git(parent, "commit", "-am", "parent: add submodule")
    old_head = git(parent, "rev-parse", "HEAD").stdout.strip()
    (parent / "README.md").write_text("dirty\n")

    result = run_tool(parent, "vendor/lib")

    assert result.returncode != 0
    assert "clean working tree" in result.stderr
    assert git(parent, "rev-parse", "HEAD").stdout.strip() == old_head
    assert (parent / ".gitmodules").exists()
