#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pycookiecheat", "pytest"]
# ///

from __future__ import annotations

import importlib.util
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import Any, cast

SCRIPT_PATH = Path(__file__).parent.parent / "python" / "notion-fetch-to-repo"
PAGE_ID = "00000000-0000-0000-0000-000000000001"
DREW = "00000000-0000-0000-0000-0000000000d0"
DAN = "00000000-0000-0000-0000-0000000000da"
USERS = {
    DREW: {"id": DREW, "name": "Drew Hoskins", "email": ""},
    DAN: {"id": DAN, "name": "Dan Davison", "email": "dan.davison@temporal.io"},
}


def load_module() -> ModuleType:
    loader = SourceFileLoader("notion_fetch_to_repo", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


def block(bid: str, kind: str, title: str | None = None, **rest: Any) -> dict[str, Any]:
    properties = {"title": [[title]]} if title is not None else {}
    return {"id": bid, "type": kind, "properties": properties, **rest}


def page_blocks(*children: dict[str, Any]) -> dict[str, Any]:
    blocks = {
        PAGE_ID: block(
            PAGE_ID, "page", "A page", content=[c["id"] for c in children if c]
        )
    }
    for child in children:
        blocks[child["id"]] = child
    return blocks


def revision(module: Any, blocks: dict[str, Any], **rest: Any) -> Any:
    return module.Revision(
        blocks=blocks,
        discussions=rest.pop("discussions", {}),
        comments=rest.pop("comments", {}),
        time_ms=rest.pop("time_ms", 1700000000000),
        author_ids=rest.pop("author_ids", [DREW]),
        label=rest.pop("label", "snapshot x"),
        users=rest.pop("users", USERS),
    )


def test_renders_block_types_to_markdown() -> None:
    module = cast(Any, load_module())
    bullet = block("b1", "bulleted_list", "first")
    nested = block("b2", "bulleted_list", "nested")
    bullet["content"] = [nested["id"]]
    blocks = page_blocks(
        block("h1", "header", "Heading"),
        block("t1", "text", "Some prose."),
        bullet,
        nested,
        block("n1", "numbered_list", "one"),
        block("n2", "numbered_list", "two"),
        block(
            "d1",
            "to_do",
            "done",
            properties={"title": [["done"]], "checked": [["Yes"]]},
        ),
        block(
            "c1",
            "code",
            "print(1)",
            properties={"title": [["print(1)"]], "language": [["Python"]]},
        ),
        block("q1", "quote", "quoted"),
        block("hr", "divider"),
    )
    blocks[PAGE_ID]["content"] = ["h1", "t1", "b1", "n1", "n2", "d1", "c1", "q1", "hr"]

    markdown = module.render_revision(revision(module, blocks), PAGE_ID)

    assert markdown == (
        "# A page\n"
        "\n"
        "## Heading\n"
        "\n"
        "Some prose.\n"
        "\n"
        "- first\n"
        "  - nested\n"
        "1. one\n"
        "2. two\n"
        "- [x] done\n"
        "\n"
        "```python\n"
        "print(1)\n"
        "```\n"
        "\n"
        "> quoted\n"
        "\n"
        "---\n"
    )


def test_renders_tables_from_rows_keyed_by_column_id() -> None:
    module = cast(Any, load_module())
    table = {
        "id": "tb1",
        "type": "table",
        "format": {
            "table_block_column_order": ["colA", "colB"],
            "table_block_column_header": True,
        },
        "content": ["r1", "r2"],
    }
    header = {
        "id": "r1",
        "type": "table_row",
        "properties": {"colA": [["Scenario"]], "colB": [["What happens"]]},
    }
    row = {
        "id": "r2",
        "type": "table_row",
        "properties": {"colA": [["Pause | resume"]], "colB": [["two\nlines"]]},
    }
    blocks = page_blocks(table, header, row)
    blocks[PAGE_ID]["content"] = ["tb1"]

    markdown = module.render_revision(revision(module, blocks), PAGE_ID)

    assert markdown == (
        "# A page\n"
        "\n"
        "| Scenario | What happens |\n"
        "| --- | --- |\n"
        "| Pause \\| resume | two<br>lines |\n"
    )


def test_renders_rich_text_decorations() -> None:
    module = cast(Any, load_module())
    segments = [
        ["bold", [["b"]]],
        [" "],
        ["code", [["c"]]],
        [" "],
        ["link", [["a", "https://example.com"]]],
        [" "],
        ["‣", [["u", DAN]]],
    ]
    blocks = page_blocks(
        {"id": "t1", "type": "text", "properties": {"title": segments}}
    )

    markdown = module.render_revision(revision(module, blocks), PAGE_ID)

    assert "**bold** `code` [link](https://example.com) @Dan Davison" in markdown


def test_renders_comments_as_of_the_snapshot() -> None:
    module = cast(Any, load_module())
    blocks = page_blocks(block("t1", "text", "annotated"))
    rev = revision(
        module,
        blocks,
        discussions={"d1": {"id": "d1", "parent_id": "t1", "context": [["annotated"]]}},
        comments={
            "c1": {
                "id": "c1",
                "parent_id": "d1",
                "created_by_id": DREW,
                "created_time": 1700000000000,
                "text": [["a remark"]],
            }
        },
    )

    markdown = module.render_revision(rev, PAGE_ID)

    assert "## Comments" in markdown
    assert 'On "annotated"' in markdown
    assert "**Drew Hoskins**" in markdown
    assert "a remark" in markdown


def test_commits_one_revision_per_change_with_notion_authorship(tmp_path: Path) -> None:
    module = cast(Any, load_module())
    first = revision(
        module,
        page_blocks(block("t1", "text", "one")),
        time_ms=1600000000000,
        author_ids=[DREW],
    )
    unchanged = revision(
        module,
        page_blocks(block("t1", "text", "one")),
        time_ms=1600000100000,
        author_ids=[DAN],
    )
    second = revision(
        module,
        page_blocks(block("t1", "text", "two")),
        time_ms=1600000200000,
        author_ids=[DAN],
        label="current",
    )

    out = tmp_path / "repo"
    module.build_repo(out, PAGE_ID, [first, unchanged, second])

    log = git(out, "log", "--format=%at|%an|%ae|%s", "--reverse")
    assert log == [
        f"1600000000|Drew Hoskins|{DREW}@users.notion.so|{module.fmt_time(1600000000000)}",
        f"1600000200|Dan Davison|dan.davison@temporal.io|{module.fmt_time(1600000200000)}",
    ]
    assert "two" in (out / "page.md").read_text()


def test_snapshots_are_ordered_oldest_first(monkeypatch) -> None:
    module = cast(Any, load_module())
    responses = {
        "snapshots": [
            {"id": "b", "timestamp": "200", "parent_id": PAGE_ID},
            {"id": "a", "timestamp": "100", "parent_id": PAGE_ID},
            {"id": "other", "timestamp": "150", "parent_id": "some-collection"},
        ]
    }
    calls: list[tuple[str, dict[str, Any], str | None]] = []

    def api_post(path: str, body: dict[str, Any], token: str, space_id=None):
        calls.append((path, body, space_id))
        return responses

    monkeypatch.setattr(module, "api_post", api_post)
    snapshots = module.list_snapshots(PAGE_ID, "space", "token")

    assert [s["id"] for s in snapshots] == ["a", "b"]
    assert calls[0][0] == "getSnapshotsList"
    assert calls[0][2] == "space", "version history needs the space routing header"


def test_skips_snapshots_whose_contents_notion_has_discarded(monkeypatch) -> None:
    """Notion keeps listing snapshots long after it stops serving their blocks."""
    module = cast(Any, load_module())
    snapshots = [
        {"id": "kept", "timestamp": "100", "authors": [{"id": DREW}]},
        {"id": "discarded", "timestamp": "200", "authors": [{"id": DAN}]},
    ]

    def api_post(path: str, body: dict[str, Any], token: str, space_id=None):
        assert path == "getSnapshotContents"
        if body["timestamp"] == "200":
            return {"contentMap": {"__version__": 3, "space": {}}}
        return {"contentMap": {"block": page_blocks(block("t1", "text", "one"))}}

    monkeypatch.setattr(module, "api_post", api_post)
    revisions = module.fetch_snapshot_revisions(
        PAGE_ID, "space", snapshots, "token", jobs=2
    )

    assert [rev.label for rev in revisions] == ["snapshot kept"]


def git(cwd: Path, *args: str) -> list[str]:
    out = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()
