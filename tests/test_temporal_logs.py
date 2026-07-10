#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest", "httpx"]
# ///
"""Tests for the temporal-logs script (offline logic: time/duration parsing, rendering)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "python" / "temporal-logs"


def load_module():
    loader = SourceFileLoader("temporal_logs", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader("temporal_logs", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["temporal_logs"] = module
    loader.exec_module(module)
    return module


tl = load_module()


class TestParseDuration:
    @pytest.mark.parametrize(
        "text,seconds",
        [
            ("30s", 30),
            ("15m", 900),
            ("1h", 3600),
            ("2d", 172800),
            ("1w", 604800),
            (" 5m ", 300),
        ],
    )
    def test_valid(self, text, seconds):
        assert tl.parse_duration(text).total_seconds() == seconds

    @pytest.mark.parametrize("text", ["5x", "abc", "", "1.5h", "h"])
    def test_invalid(self, text):
        with pytest.raises(tl.QueryError):
            tl.parse_duration(text)


class TestParseTime:
    NOW = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)

    def test_now(self):
        assert tl.parse_time("now", self.NOW) == self.NOW

    def test_iso_z(self):
        assert tl.parse_time("2025-08-10T15:03:59Z", self.NOW) == datetime(
            2025, 8, 10, 15, 3, 59, tzinfo=timezone.utc
        )

    def test_naive_assumes_utc(self):
        assert tl.parse_time("2025-08-10T15:03:59", self.NOW).tzinfo == timezone.utc

    def test_invalid(self):
        with pytest.raises(tl.QueryError):
            tl.parse_time("notatime", self.NOW)


class TestTimeRange:
    def test_since_window(self):
        args = _ns(since="1h", from_=None, to="2026-07-10T12:00:00Z")
        tr = tl.resolve_time_range(args)
        assert tr.end_ns - tr.start_ns == 3600 * 1_000_000_000

    def test_from_overrides_since(self):
        args = _ns(since="1h", from_="2026-07-10T10:00:00Z", to="2026-07-10T12:00:00Z")
        tr = tl.resolve_time_range(args)
        assert tr.end_ns - tr.start_ns == 2 * 3600 * 1_000_000_000

    def test_start_after_end_rejected(self):
        args = _ns(since="1h", from_="2026-07-10T13:00:00Z", to="2026-07-10T12:00:00Z")
        with pytest.raises(tl.QueryError):
            tl.resolve_time_range(args)


class TestRender:
    def test_streams_pretty(self, capsys):
        payload = {
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"k8s_pod": "history-0"},
                        "values": [["1700000000000000000", "hello"]],
                    }
                ],
            }
        }
        tl.render(payload, "pretty", "backward", 1000)
        out = capsys.readouterr()
        assert "hello" in out.out
        assert "1 log lines" in out.err

    def test_streams_truncation_warning(self, capsys):
        payload = {
            "data": {
                "resultType": "streams",
                "result": [{"stream": {}, "values": [["1700000000000000000", "x"]]}],
            }
        }
        tl.render(payload, "raw", "backward", 1)
        assert "truncated" in capsys.readouterr().err

    def test_vector_jsonl(self, capsys):
        payload = {
            "data": {
                "resultType": "vector",
                "result": [{"metric": {"error": "boom"}, "value": [1700000000, "42"]}],
            }
        }
        tl.render(payload, "jsonl", "backward", 1000)
        assert '"value": "42"' in capsys.readouterr().out


class TestPortForwardCmd:
    def test_env_mapping(self):
        assert tl.ENVIRONMENTS["prod"]["cell"] == "o-uswe2"
        assert tl.ENVIRONMENTS["test"]["cell"] == "o-nj99p"
        cmd = tl.port_forward_cmd("o-uswe2", 3100)
        assert cmd[:3] == ["ct", "kubectl", "--context"]
        assert "service/loki-query-frontend" in cmd


class TestCli:
    def test_help(self):
        r = subprocess.run([str(SCRIPT_PATH), "--help"], capture_output=True, text=True)
        assert r.returncode == 0
        assert "LogQL" in r.stdout or "query" in r.stdout


class TestEnsureLoki:
    def test_addr_overrides_forward(self):
        args = _ns(addr="http://example:3100/", env="prod", no_forward=False)
        assert tl.ensure_loki(args) == "http://example:3100"

    def test_no_forward_errors_when_unreachable(self, monkeypatch):
        monkeypatch.setattr(tl, "loki_ready", lambda addr: False)
        args = _ns(addr=None, env="prod", no_forward=True)
        with pytest.raises(tl.QueryError, match="no Loki"):
            tl.ensure_loki(args)


def _ns(**kw):
    import argparse

    return argparse.Namespace(**kw)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
