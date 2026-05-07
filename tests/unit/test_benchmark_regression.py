import json
import os
import tempfile

import pytest

from aio.benchmark.collector import BenchmarkSnapshot, NodeSnapshot
from aio.benchmark.regression import RegressionDetector
from aio.benchmark.runner import BenchmarkResult, ScenarioResult


class TestRegressionDetector:
    def _make_result(self, e2e_p50: float, throughput: float, node_p50: float = 0.1) -> BenchmarkResult:
        sr = ScenarioResult(
            name="echo",
            snapshot=BenchmarkSnapshot(
                node_snapshots={
                    "node_a": NodeSnapshot(
                        latencies=[node_p50] * 10,
                        statuses=["ok"] * 10,
                    )
                },
                e2e_times=[e2e_p50] * 10,
                throughput=throughput,
                iterations=10,
            ),
            input_text="hello",
            iterations=10,
            warmup_iterations=0,
        )
        return BenchmarkResult(
            timestamp="2024-01-01T00:00:00Z",
            python_version="3.12",
            git_commit=None,
            scenario_results=[sr],
        )

    def _write_baseline(self, e2e_p50: float, throughput: float, node_p50: float = 0.1) -> str:
        baseline = {
            "scenarios": [
                {
                    "name": "echo",
                    "e2e_p50": e2e_p50,
                    "e2e_p99": e2e_p50,
                    "e2e_mean": e2e_p50,
                    "throughput": throughput,
                    "node_stats": {
                        "node_a": {"p50": node_p50, "p99": node_p50},
                    },
                }
            ]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(baseline, fh)
        return path

    def test_no_regression_when_within_threshold(self):
        baseline_path = self._write_baseline(e2e_p50=1.0, throughput=1.0)
        current = self._make_result(e2e_p50=1.05, throughput=0.95)
        detector = RegressionDetector(threshold_percent=10.0)
        report = detector.compare(current, baseline_path)
        assert report.passed is True
        assert not report.regressions

    def test_flags_latency_regression(self):
        baseline_path = self._write_baseline(e2e_p50=1.0, throughput=1.0)
        current = self._make_result(e2e_p50=1.2, throughput=1.0)
        detector = RegressionDetector(threshold_percent=10.0)
        report = detector.compare(current, baseline_path)
        assert report.passed is False
        assert any(r.metric == "e2e_p50" for r in report.regressions)

    def test_flags_throughput_regression(self):
        baseline_path = self._write_baseline(e2e_p50=1.0, throughput=1.0)
        current = self._make_result(e2e_p50=1.0, throughput=0.8)
        detector = RegressionDetector(threshold_percent=10.0)
        report = detector.compare(current, baseline_path)
        assert report.passed is False
        assert any(r.metric == "throughput" for r in report.regressions)

    def test_flags_node_p99_regression(self):
        baseline_path = self._write_baseline(e2e_p50=1.0, throughput=1.0, node_p50=0.1)
        current = self._make_result(e2e_p50=1.0, throughput=1.0, node_p50=0.2)
        detector = RegressionDetector(threshold_percent=10.0)
        report = detector.compare(current, baseline_path)
        assert report.passed is False
        assert any(r.metric == "node_a.p50" for r in report.regressions)

    def test_report_to_dict(self):
        baseline_path = self._write_baseline(e2e_p50=1.0, throughput=1.0)
        current = self._make_result(e2e_p50=1.2, throughput=1.0)
        detector = RegressionDetector(threshold_percent=10.0)
        report = detector.compare(current, baseline_path)
        d = report.to_dict()
        assert d["passed"] is False
        assert len(d["regressions"]) > 0
