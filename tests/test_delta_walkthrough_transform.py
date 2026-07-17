#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
"""Tests for delta-walkthrough-transform.

Fixture: a 20-line file L1..L20 that (per the *original*, pre-walkthrough diff)
had two lines ADDED1/ADDED2 inserted after L10, with 3 lines of context on each
side, then run through code-walkthrough's build-walkthrough with one step and
one 2-line "// ▶" comment. Expected outputs below were computed by hand from
build-walkthrough's own formulas (see script docstring), not from the script
under test, so these are real assertions, not tautologies.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent.parent / "python" / "delta-walkthrough-transform"

FILE_HEADER = (
    "diff --git a/sample.go b/sample.go\n"
    "index 1111111..2222222 100644\n"
    "--- a/sample.go\n"
    "+++ b/sample.go\n"
)

ORIGINAL_HUNK = (
    "@@ -8,6 +6,10 @@\n"
    " L8\n"
    " L9\n"
    " L10\n"
    "+// ▶ [WALKTHROUGH 1/1]\n"
    "+// ▶ This step adds two lines.\n"
    "+ADDED1\n"
    "+ADDED2\n"
    " L11\n"
    " L12\n"
    " L13\n"
)

WALKTHROUGH_DIFF = FILE_HEADER + ORIGINAL_HUNK

NEW_FILE_LINES = (
    [f"L{n}\n" for n in range(1, 11)]
    + ["ADDED1\n", "ADDED2\n"]
    + [f"L{n}\n" for n in range(11, 21)]
)


def run(input_text: str, context: int, cwd: Path) -> str:
    result = subprocess.run(
        [str(SCRIPT_PATH), "--context", str(context)],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def write_repo(tmp_path: Path) -> Path:
    (tmp_path / "sample.go").write_text("".join(NEW_FILE_LINES))
    return tmp_path


def test_contract_trims_existing_context_no_file_needed(tmp_path):
    # No sample.go on disk: contraction must not need to read the file.
    out = run(WALKTHROUGH_DIFF, context=1, cwd=tmp_path)
    expected = FILE_HEADER + (
        "@@ -10,2 +8,6 @@\n"
        " L10\n"
        "+// ▶ [WALKTHROUGH 1/1]\n"
        "+// ▶ This step adds two lines.\n"
        "+ADDED1\n"
        "+ADDED2\n"
        " L11\n"
    )
    assert out == expected


def test_contract_to_zero_context(tmp_path):
    out = run(WALKTHROUGH_DIFF, context=0, cwd=tmp_path)
    expected = FILE_HEADER + (
        "@@ -11,0 +9,4 @@\n"
        "+// ▶ [WALKTHROUGH 1/1]\n"
        "+// ▶ This step adds two lines.\n"
        "+ADDED1\n"
        "+ADDED2\n"
    )
    assert out == expected


def test_expand_pulls_extra_lines_from_working_tree(tmp_path):
    repo = write_repo(tmp_path)
    out = run(WALKTHROUGH_DIFF, context=5, cwd=repo)
    expected = FILE_HEADER + (
        "@@ -6,10 +4,14 @@\n"
        " L6\n"
        " L7\n"
        " L8\n"
        " L9\n"
        " L10\n"
        "+// ▶ [WALKTHROUGH 1/1]\n"
        "+// ▶ This step adds two lines.\n"
        "+ADDED1\n"
        "+ADDED2\n"
        " L11\n"
        " L12\n"
        " L13\n"
        " L14\n"
        " L15\n"
    )
    assert out == expected


def test_expand_clamps_at_file_boundary(tmp_path):
    repo = write_repo(tmp_path)
    # File only has 22 lines; requesting huge context must clamp, not crash
    # or read past either end. new_start would compute to -1 (11 - 2 - 10);
    # build-walkthrough's own max(1, ...) clamp applies here too.
    out = run(WALKTHROUGH_DIFF, context=1000, cwd=repo)
    lines = out.splitlines()
    header = lines[len(FILE_HEADER.splitlines())]
    assert header == "@@ -1,20 +1,24 @@"
    body = out[len(FILE_HEADER) :]
    ctx_lines = [ln[1:] for ln in body.splitlines() if ln.startswith(" ")]
    assert ctx_lines == [f"L{n}" for n in range(1, 11)] + [
        f"L{n}" for n in range(11, 21)
    ]


def test_expand_without_file_on_disk_leaves_context_unchanged(tmp_path):
    # File missing entirely (e.g. deleted, or not actually at HEAD): can't
    # manufacture new context, so expansion is a no-op rather than an error.
    out = run(WALKTHROUGH_DIFF, context=5, cwd=tmp_path)
    expected = FILE_HEADER + ORIGINAL_HUNK
    assert out == expected


def test_summary_block_passed_through_unchanged(tmp_path):
    summary = (
        "diff --git a/sample.go b/sample.go\n"
        "index 1111111..2222222 100644\n"
        "--- a/sample.go\n"
        "+++ b/sample.go\n"
        "@@ -1,0 +1,2 @@\n"
        "+// ▶ [WALKTHROUGH 0/1]\n"
        "+// ▶ Summary of the whole branch.\n"
    ) + ORIGINAL_HUNK
    repo = write_repo(tmp_path)
    out = run(summary, context=5, cwd=repo)
    assert out.startswith(
        "diff --git a/sample.go b/sample.go\n"
        "index 1111111..2222222 100644\n"
        "--- a/sample.go\n"
        "+++ b/sample.go\n"
        "@@ -1,0 +1,2 @@\n"
        "+// ▶ [WALKTHROUGH 0/1]\n"
        "+// ▶ Summary of the whole branch.\n"
    )


def test_two_hunks_expansion_does_not_overlap(tmp_path):
    # Second file state: L1..L10, ADDED1, ADDED2, L11..L16, ADDED3, L17..L20.
    file_lines = (
        [f"L{n}\n" for n in range(1, 11)]
        + ["ADDED1\n", "ADDED2\n"]
        + [f"L{n}\n" for n in range(11, 17)]
        + ["ADDED3\n"]
        + [f"L{n}\n" for n in range(17, 21)]
    )
    (tmp_path / "sample.go").write_text("".join(file_lines))

    second_hunk = (
        "@@ -16,3 +16,6 @@\n"
        " L16\n"
        "+// ▶ [WALKTHROUGH 2/2]\n"
        "+// ▶ Second step.\n"
        "+ADDED3\n"
        " L17\n"
        " L18\n"
    )
    diff = FILE_HEADER + ORIGINAL_HUNK + second_hunk
    out = run(diff, context=1000, cwd=tmp_path)
    body = out[len(FILE_HEADER) :]
    ctx_lines = [ln[1:].rstrip("\n") for ln in body.splitlines() if ln.startswith(" ")]
    # Every real line appears exactly once, split cleanly across the two hunks.
    assert ctx_lines == [f"L{n}" for n in range(1, 21)]
