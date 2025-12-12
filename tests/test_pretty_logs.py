#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
"""Tests for pretty-logs script.

The CRITICAL invariant: pretty-logs must NEVER drop log lines.
Every input line must produce output (either prettified or raw).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "python" / "pretty-logs"


def run_pretty_logs(input_text: str) -> tuple[str, str, int]:
    """Run pretty-logs via subprocess and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        [str(SCRIPT_PATH)],
        input=input_text,
        capture_output=True,
        text=True,
    )
    return result.stdout, result.stderr, result.returncode


# =============================================================================
# CRITICAL: Never Drop Lines Tests
# =============================================================================


class TestNeverDropLines:
    """The most critical invariant: no input line should ever be silently dropped."""

    def test_plain_text_lines_pass_through(self):
        """Plain text without JSON should pass through unchanged."""
        input_lines = [
            "plain text line",
            "another line without json",
            "INFO: already formatted",
        ]
        input_text = "\n".join(input_lines) + "\n"
        stdout, stderr, rc = run_pretty_logs(input_text)

        for line in input_lines:
            assert line in stdout, f"Line was dropped: {line!r}"

    def test_empty_and_whitespace_lines(self):
        """Empty and whitespace lines should pass through."""
        input_text = "before\n\n   \nafter\n"
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "before" in stdout
        assert "after" in stdout

    def test_malformed_json_prints_raw(self):
        """Lines with { but invalid JSON should print raw."""
        input_lines = [
            "prefix {not valid json",
            "{unclosed",
            'partial {"key": "value"',
        ]
        input_text = "\n".join(input_lines) + "\n"
        stdout, stderr, rc = run_pretty_logs(input_text)

        for line in input_lines:
            assert line in stdout, f"Malformed JSON line was dropped: {line!r}"

    def test_valid_json_produces_output(self):
        """Valid JSON log lines should produce output."""
        input_lines = [
            '{"level": "info", "msg": "hello"}',
            '{"level": "error", "msg": "failed"}',
            '{"level": "warn", "msg": "warning"}',
            '{"msg": "no level"}',
            '{"no_msg": true}',
        ]
        input_text = "\n".join(input_lines) + "\n"
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert stdout.strip(), "No output produced for valid JSON"
        assert "hello" in stdout
        assert "failed" in stdout
        assert "warning" in stdout

    def test_zap_console_format_produces_output(self):
        """Zap console encoder format should be parsed and produce output."""
        input_lines = [
            '2025-12-10T08:36:15.591-0500\tINFO\treflect/value.go:581\tcreating cleaner\t{"Namespace": "default"}',
            '2025-12-10T08:36:15.591-0500\tERROR\tapp.go:42\tsomething failed\t{"error": "connection refused"}',
            '2025-12-10T08:36:15.591-0500\tWARN\tutil.go:10\twarning message\t{"count": 5}',
        ]
        input_text = "\n".join(input_lines) + "\n"
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "creating cleaner" in stdout
        # ERROR shows full JSON, so check for content
        assert "something failed" in stdout or "connection refused" in stdout
        assert "warning message" in stdout or "count" in stdout

    def test_mixed_input_all_lines_processed(self):
        """Mixed valid/invalid/plain lines should all produce output."""
        input_lines = [
            "plain text",
            '{"level": "info", "msg": "json msg"}',
            "malformed {json",
            '2025-12-10T08:36:15.591-0500\tINFO\tfile.go:1\tzap format\t{"key": "val"}',
            "another plain line",
        ]
        input_text = "\n".join(input_lines) + "\n"
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "plain text" in stdout
        assert "json msg" in stdout
        assert "malformed {json" in stdout
        assert "zap format" in stdout
        assert "another plain line" in stdout

    def test_output_has_content_for_each_input(self):
        """Each input line should contribute to output."""
        input_lines = [
            "line 1",
            "line 2",
            '{"level": "info", "msg": "line 3"}',
            '{"level": "error", "msg": "line 4"}',
            "line 5",
        ]
        input_text = "\n".join(input_lines) + "\n"
        stdout, stderr, rc = run_pretty_logs(input_text)

        # Count non-empty output lines
        output_lines = [l for l in stdout.split("\n") if l.strip()]
        assert len(output_lines) >= 5, f"Too few output lines: {output_lines}"


# =============================================================================
# Level Detection Tests
# =============================================================================


class TestLevelDetection:
    """Tests for log level detection and formatting."""

    def test_info_level_condensed(self):
        """INFO level should produce condensed output."""
        input_text = '{"level": "info", "msg": "hello world"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "INFO: hello world" in stdout

    def test_info_from_zap_prefix(self):
        """INFO from zap prefix should produce condensed output."""
        input_text = '2025-12-10T08:36:15.591-0500\tINFO\tfile.go:1\thello world\t{"key": "val"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "INFO: hello world" in stdout

    def test_error_level_shows_full_json(self):
        """ERROR level should show full JSON."""
        input_text = '{"level": "error", "msg": "failed", "details": "more info"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "details" in stdout
        assert "more info" in stdout

    def test_warn_level_shows_full_json(self):
        """WARN level should show full JSON."""
        input_text = '{"level": "warn", "msg": "warning", "count": 5}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "count" in stdout

    def test_debug_treated_as_info(self):
        """DEBUG level should be condensed like INFO."""
        input_text = '{"level": "debug", "msg": "debug message"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "INFO: debug message" in stdout

    def test_warning_alias_for_warn(self):
        """'warning' should be treated as WARN."""
        input_text = '{"level": "warning", "msg": "a warning"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        # WARN shows full JSON
        assert "a warning" in stdout

    def test_unknown_level_shows_full_json(self):
        """Unknown level should show full JSON."""
        input_text = '{"level": "trace", "msg": "trace message"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        # Falls through to case _, shows full JSON
        assert "trace" in stdout
        assert "trace message" in stdout

    def test_no_level_shows_full_json(self):
        """Missing level should show full JSON."""
        input_text = '{"msg": "no level field", "extra": "data"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "extra" in stdout
        assert "data" in stdout


# =============================================================================
# Ignored Errors Tests
# =============================================================================


class TestIgnoredErrors:
    """Tests for error filtering."""

    def test_ignored_error_condensed(self):
        """Errors matching IGNORE_ERRORS should be condensed like INFO."""
        input_text = '{"level": "error", "msg": "ignored", "error": "container not found (\\"admin-tools\\")"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        # Should be condensed, not show full JSON
        assert "IGNORED_ERROR: ignored" in stdout

    def test_non_ignored_error_full_json(self):
        """Errors not matching IGNORE_ERRORS should show full JSON."""
        input_text = '{"level": "error", "msg": "real error", "error": "connection refused"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "connection refused" in stdout


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge cases and corner cases."""

    def test_nested_json(self):
        """Nested JSON should be handled."""
        input_text = '{"level": "info", "msg": "test", "data": {"nested": true}}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "test" in stdout

    def test_json_with_newlines_in_string(self):
        """JSON with escaped newlines should be handled."""
        input_text = '{"level": "info", "msg": "hello\\nworld"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "hello" in stdout

    def test_very_long_line(self):
        """Very long lines should not be dropped."""
        long_value = "x" * 10000
        input_text = f'{{"level": "info", "msg": "test", "long": "{long_value}"}}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "test" in stdout

    def test_unicode_content(self):
        """Unicode content should be handled."""
        input_text = '{"level": "info", "msg": "emoji 🎉 and unicode ñ"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "emoji" in stdout

    def test_empty_json_object(self):
        """Empty JSON object should produce output."""
        input_text = "{}\n"
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert stdout.strip(), "Empty JSON should produce output"

    def test_json_array_prints_raw(self):
        """JSON array should print raw (not a valid log entry)."""
        input_text = "[1, 2, 3]\n"
        stdout, stderr, rc = run_pretty_logs(input_text)
        # Should print error and raw line
        assert "[1, 2, 3]" in stdout

    def test_stacktrace_formatting(self):
        """Stacktrace field should be formatted."""
        input_text = '{"level": "error", "msg": "crash", "stacktrace": "line1\\nline2"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "crash" in stdout

    def test_info_with_no_msg_shows_json(self):
        """INFO with no msg field should show full JSON."""
        input_text = '{"level": "info", "key": "value", "count": 42}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)
        # No msg, so should serialize the JSON
        assert "key" in stdout or "value" in stdout

    def test_zap_format_with_spaces(self):
        """Zap format with spaces (not tabs) should still work."""
        input_text = '2025-12-10T08:36:15.591-0500    INFO    file.go:1    message here    {"key": "val"}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "message here" in stdout


# =============================================================================
# Real-world Examples
# =============================================================================


class TestRealWorldExamples:
    """Tests based on real log formats seen in the wild."""

    def test_temporal_bench_log(self):
        """Real example from temporal-bench."""
        input_text = (
            '2025-12-10T08:36:15.591-0500\tINFO\treflect/value.go:581\tcreating cleaner\t'
            '{"Namespace": "default", "TaskQueue": "temporal-bench", "WorkerID": "worker-0@28325@dan-2.local@temporal-bench"}\n'
        )
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "creating cleaner" in stdout

    def test_simple_server_log(self):
        """Simple server-style JSON log."""
        input_text = '{"ts":"2025-12-10T08:36:15Z","level":"info","msg":"Server started","port":8080}\n'
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "Server started" in stdout


# =============================================================================
# Go Stack Trace Handling
# =============================================================================


class TestGoStackTraces:
    """Tests for Go stack trace continuation line handling."""

    def test_stack_trace_function_line_not_dropped(self):
        """Go stack trace function lines should not be dropped."""
        input_text = "go.temporal.io/sdk/internal.(*baseWorker).runPoller.func1\n"
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "runPoller" in stdout

    def test_stack_trace_file_line_not_dropped(self):
        """Go stack trace file lines should not be dropped."""
        input_text = "\t/Users/dan/go/pkg/mod/go.temporal.io/sdk@v1.38.0/internal/internal_worker_base.go:486\n"
        stdout, stderr, rc = run_pretty_logs(input_text)
        # Check for parts that won't be affected by line wrapping
        assert "/Users/dan/go" in stdout
        assert ":486" in stdout

    def test_stack_trace_with_spaces_not_dropped(self):
        """Go stack trace file lines with spaces should not be dropped."""
        input_text = "        /Users/dan/go/pkg/mod/something.go:123\n"
        stdout, stderr, rc = run_pretty_logs(input_text)
        assert "something.go" in stdout

    def test_full_error_with_stack_trace(self):
        """Full error log followed by stack trace should all appear."""
        input_lines = [
            '2025-12-10T08:42:28.415-0500\tWARN\tinternal/worker.go:486\tFailed to poll\t{"Error": "not found"}',
            "go.temporal.io/sdk/internal.(*baseWorker).runPoller.func1",
            "\t/Users/dan/go/pkg/mod/go.temporal.io/sdk@v1.38.0/internal/worker.go:486",
            "go.temporal.io/sdk/internal.(*baseWorker).runPoller",
            "\t/Users/dan/go/pkg/mod/go.temporal.io/sdk@v1.38.0/internal/worker.go:492",
        ]
        input_text = "\n".join(input_lines) + "\n"
        stdout, stderr, rc = run_pretty_logs(input_text)

        # Main error should appear
        assert "Failed to poll" in stdout or "not found" in stdout
        # Stack trace lines should not be dropped
        assert "runPoller" in stdout
        assert "worker.go:486" in stdout

    def test_mixed_logs_and_stack_traces(self):
        """Interleaved normal logs and stack traces should all appear."""
        input_lines = [
            "INFO: normal log line",
            "go.temporal.io/sdk/internal.SomeFunction",
            "\t/path/to/file.go:100",
            '{"level": "info", "msg": "another log"}',
        ]
        input_text = "\n".join(input_lines) + "\n"
        stdout, stderr, rc = run_pretty_logs(input_text)

        assert "normal log line" in stdout
        assert "SomeFunction" in stdout
        assert "file.go:100" in stdout
        assert "another log" in stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
