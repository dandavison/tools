#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pycookiecheat", "pytest"]
# ///

from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import Any, cast

SCRIPT_PATH = Path(__file__).parent.parent / "python" / "notion-fetch"
ROOT_ID = "00000000-0000-0000-0000-000000000001"
TOGGLE_ID = "00000000-0000-0000-0000-000000000002"
BLOCK_ID = "00000000-0000-0000-0000-000000000003"
DISCUSSION_ID = "00000000-0000-0000-0000-000000000004"
COMMENT_ID = "00000000-0000-0000-0000-000000000005"


def load_module() -> ModuleType:
    loader = SourceFileLoader("notion_fetch", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


def record(value: dict[str, Any]) -> dict[str, Any]:
    return {"value": value}


def test_loads_comments_from_toggleable_descendant_chunks() -> None:
    notion_fetch = cast(Any, load_module())
    calls: list[tuple[str, dict[str, Any]]] = []

    root_response = {
        "recordMap": {
            "block": {
                ROOT_ID: record(
                    {"id": ROOT_ID, "content": [TOGGLE_ID], "space_id": "space"}
                ),
                TOGGLE_ID: record(
                    {
                        "id": TOGGLE_ID,
                        "parent_id": ROOT_ID,
                        "type": "sub_header",
                        "format": {"toggleable": True},
                        "content": [BLOCK_ID],
                        "space_id": "space",
                    }
                ),
                BLOCK_ID: record(
                    {"id": BLOCK_ID, "parent_id": TOGGLE_ID, "type": "text"}
                ),
            }
        },
        "cursor": {},
    }
    descendant_response = {
        "recordMap": {
            "discussion": {
                DISCUSSION_ID: record({"id": DISCUSSION_ID, "parent_id": BLOCK_ID})
            },
            "comment": {
                COMMENT_ID: record(
                    {
                        "id": COMMENT_ID,
                        "parent_id": DISCUSSION_ID,
                        "text": [["A descendant comment"]],
                    }
                )
            },
        }
    }

    def api_post(path: str, body: dict[str, Any], token: str) -> dict[str, Any]:
        calls.append((path, body))
        if path == "loadPageChunk":
            return root_response
        assert path == "loadCachedPageChunks"
        assert [request["page"]["id"] for request in body["requests"]] == [TOGGLE_ID]
        return descendant_response

    notion_fetch.api_post = api_post
    records = notion_fetch.load_page_records(ROOT_ID, "token")

    assert list(records["comment"]) == [COMMENT_ID]
    assert [path for path, _ in calls] == ["loadPageChunk", "loadCachedPageChunks"]
