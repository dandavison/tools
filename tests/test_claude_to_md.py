#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
"""Tests for claude-to-md: reflow a Claude Code transcript into markdown."""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent.parent / "python" / "claude-to-md"

TRANSCRIPT = """\
❯ I'm imagining watching the sequence of ItemDescriptors being sent to the server in chunks, and some starting to be dispatched in
  activity tasks to a worker. Some fail. Can you talk me through what happens next in terms of retries? Does each item follow the
  state machine with its associated retry policy?

⏺ Let me walk it through, taking your batch of 1000 with, say, 950 successes and 50 failures.

  The completion. The worker returns one batch-completion RPC: 950 outcomes-with-evidence, 50 failures-with-errors, plus the
  capacity lease and observed costs.

  Your second question — yes for the logical machine, no for the physical machinery. Each item individually follows the activity
  state-machine states and retry-policy semantics.
"""

EXPECTED = """\
> I'm imagining watching the sequence of ItemDescriptors being sent to the server in chunks, and some starting to be dispatched in activity tasks to a worker. Some fail. Can you talk me through what happens next in terms of retries? Does each item follow the state machine with its associated retry policy?

Let me walk it through, taking your batch of 1000 with, say, 950 successes and 50 failures.

The completion. The worker returns one batch-completion RPC: 950 outcomes-with-evidence, 50 failures-with-errors, plus the capacity lease and observed costs.

Your second question — yes for the logical machine, no for the physical machinery. Each item individually follows the activity state-machine states and retry-policy semantics.
"""


def run(input_text: str) -> str:
    result = subprocess.run(
        [str(SCRIPT_PATH)], input=input_text, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_reflow():
    assert run(TRANSCRIPT) == EXPECTED


def test_multiple_turns():
    text = "❯ first\n  question\n\n⏺ first answer\n\n❯ second question\n\n⏺ second\n  answer\n"
    assert (
        run(text)
        == "> first question\n\nfirst answer\n\n> second question\n\nsecond answer\n"
    )


def test_multi_paragraph_prompt():
    text = "❯ para one\n\n  para two\n\n⏺ answer\n"
    assert run(text) == "> para one\n>\n> para two\n\nanswer\n"


def test_no_trailing_whitespace_in_output():
    out = run(TRANSCRIPT)
    assert all(line == line.rstrip() for line in out.splitlines())
