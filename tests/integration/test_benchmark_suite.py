import pytest

from aio.benchmark.runner import BenchmarkRunner
from aio.config.models import BenchmarkConfig


class TestBenchmarkSuiteIntegration:
    def test_runner_echo_scenario(self):
        cfg = BenchmarkConfig(
            iterations=1,
            warmup_iterations=0,
            scenarios=["echo"],
            enable_memory_profiling=False,
            enable_html_report=False,
        )
        runner = BenchmarkRunner(cfg)
        result = runner.run()
        assert len(result.scenario_results) == 1
        sr = result.scenario_results[0]
        assert sr.name == "echo"
        assert sr.iterations == 1
        assert sr.e2e_mean > 0
        assert sr.throughput > 0
        assert "context.ingest" in sr.snapshot.node_snapshots or "context_ingest" in sr.snapshot.node_snapshots

    def test_runner_safety_block_scenario(self):
        cfg = BenchmarkConfig(
            iterations=1,
            warmup_iterations=0,
            scenarios=["safety_block"],
            enable_memory_profiling=False,
            enable_html_report=False,
        )
        runner = BenchmarkRunner(cfg)
        result = runner.run()
        sr = result.scenario_results[0]
        assert sr.name == "safety_block"
        assert sr.iterations == 1

    def test_runner_multiple_scenarios(self):
        cfg = BenchmarkConfig(
            iterations=1,
            warmup_iterations=0,
            scenarios=["echo", "context_overflow"],
            enable_memory_profiling=False,
            enable_html_report=False,
        )
        runner = BenchmarkRunner(cfg)
        result = runner.run()
        assert len(result.scenario_results) == 2
        names = {sr.name for sr in result.scenario_results}
        assert names == {"echo", "context_overflow"}

    def test_runner_result_has_metadata(self):
        cfg = BenchmarkConfig(
            iterations=1,
            warmup_iterations=0,
            scenarios=["echo"],
            enable_memory_profiling=False,
            enable_html_report=False,
        )
        runner = BenchmarkRunner(cfg)
        result = runner.run()
        assert result.timestamp
        assert result.python_version
        assert "benchmark_config" in result.metadata
