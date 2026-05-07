import json
import os
import tempfile

import pytest

from aio.benchmark.collector import BenchmarkSnapshot, NodeSnapshot
from aio.benchmark.reporter import HTMLReporter, JSONReporter
from aio.benchmark.runner import BenchmarkResult, ScenarioResult


class TestJSONReporter:
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = ScenarioResult(
                name="echo",
                snapshot=BenchmarkSnapshot(
                    node_snapshots={
                        "node_a": NodeSnapshot(latencies=[0.1, 0.2], statuses=["ok"])
                    },
                    e2e_times=[0.5, 0.6],
                    throughput=2.0,
                    iterations=2,
                ),
                input_text="hello",
                iterations=2,
                warmup_iterations=0,
            )
            result = BenchmarkResult(
                timestamp="2024-01-01T00:00:00Z",
                python_version="3.12",
                git_commit="abc123",
                scenario_results=[sr],
            )
            path = JSONReporter().report(result, tmpdir)
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            assert data["timestamp"] == "2024-01-01T00:00:00Z"
            assert data["git_commit"] == "abc123"
            assert len(data["scenarios"]) == 1
            assert data["scenarios"][0]["name"] == "echo"
            assert data["scenarios"][0]["node_stats"]["node_a"]["count"] == 2


class TestHTMLReporter:
    def test_contains_scenario_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = ScenarioResult(
                name="echo",
                snapshot=BenchmarkSnapshot(
                    node_snapshots={},
                    e2e_times=[0.5],
                    throughput=2.0,
                    iterations=1,
                ),
                input_text="hello",
                iterations=1,
                warmup_iterations=0,
            )
            result = BenchmarkResult(
                timestamp="2024-01-01T00:00:00Z",
                python_version="3.12",
                git_commit=None,
                scenario_results=[sr],
            )
            path = HTMLReporter().report(result, tmpdir)
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            assert "echo" in text
            assert "AIO Benchmark Report" in text

    def test_jinja2_fallback_when_unavailable(self, monkeypatch):
        monkeypatch.setattr("aio.benchmark.reporter.JINJA2_AVAILABLE", False)
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = ScenarioResult(
                name="echo",
                snapshot=BenchmarkSnapshot(
                    node_snapshots={},
                    e2e_times=[0.5],
                    throughput=2.0,
                    iterations=1,
                ),
                input_text="hello",
                iterations=1,
                warmup_iterations=0,
            )
            result = BenchmarkResult(
                timestamp="2024-01-01T00:00:00Z",
                python_version="3.12",
                git_commit=None,
                scenario_results=[sr],
            )
            path = HTMLReporter().report(result, tmpdir)
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            assert "echo" in text
