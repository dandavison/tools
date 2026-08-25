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

SCRIPT_PATH = Path(__file__).parent.parent / "python" / "notion-push"

ISSUE_MARKDOWN = """---
number: 42
date: 2026-08-25
title: "Why: the thing broke"
---

# Why: the thing broke

*Issue by @dandavison on 2026-08-25T00:00:00Z*

body
"""


def load_module() -> ModuleType:
    loader = SourceFileLoader("notion_push", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


def test_frontmatter_supplies_title_and_is_dropped_with_its_duplicate_heading() -> None:
    notion_push = cast(Any, load_module())
    title, body = notion_push.title_and_body(ISSUE_MARKDOWN, None)
    assert title == "Why: the thing broke"
    assert body.startswith("*Issue by @dandavison")
    assert "---" not in body
    assert "# Why" not in body


def test_first_heading_supplies_title() -> None:
    notion_push = cast(Any, load_module())
    title, body = notion_push.title_and_body("# Heading\n\nbody\n", None)
    assert (title, body) == ("Heading", "body\n")


def test_override_keeps_a_differing_heading() -> None:
    notion_push = cast(Any, load_module())
    title, body = notion_push.title_and_body("# Heading\n\nbody\n", "Override")
    assert (title, body) == ("Override", "# Heading\n\nbody\n")


def test_untitled_when_nothing_supplies_a_title() -> None:
    notion_push = cast(Any, load_module())
    assert notion_push.title_and_body("just prose\n", None) == (
        "Untitled",
        "just prose\n",
    )


def test_file_stem_flattens_path_separators_and_newlines() -> None:
    notion_push = cast(Any, load_module())
    assert notion_push.file_stem("a/b\nc") == "a b c"
