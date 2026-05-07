from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..config.models import AIOConfig, BenchmarkConfig
from ..graph.builder import build_aio_graph
from ..layers.observability import ObservabilityLayer
from ..state import make_initial_state
from .collector import BenchmarkCollector, BenchmarkSnapshot


@dataclass
class ScenarioResult:
    name: str
    snapshot: BenchmarkSnapshot
    input_text: str
    iterations: int
    warmup_iterations: int

    @property
    def e2e_p50(self) -> float:
        return self.snapshot.e2e_p50

    @property
    def e2e_p99(self) -> float:
        return self.snapshot.e2e_p99

    @property
    def e2e_mean(self) -> float:
        return self.snapshot.e2e_mean

    @property
    def throughput(self) -> float:
        return self.snapshot.throughput

    def to_dict(self) -> Dict[str, Any]:
        node_stats: Dict[str, Any] = {}
        for node_name, ns in self.snapshot.node_snapshots.items():
            node_stats[node_name] = {
                "p50": ns.p50,
                "p99": ns.p99,
                "mean": ns.mean,
                "count": ns.count,
                "status_counts": ns.status_counts(),
                "memory_deltas_bytes": ns.memory_deltas_bytes,
            }
        return {
            "name": self.name,
            "input_text": self.input_text,
            "iterations": self.iterations,
            "warmup_iterations": self.warmup_iterations,
            "e2e_p50": self.e2e_p50,
            "e2e_p99": self.e2e_p99,
            "e2e_mean": self.e2e_mean,
            "throughput": self.throughput,
            "memory_samples_bytes": self.snapshot.memory_samples_bytes,
            "node_stats": node_stats,
        }


@dataclass
class BenchmarkResult:
    timestamp: str
    python_version: str
    git_commit: Optional[str]
    scenario_results: List[ScenarioResult]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "python_version": self.python_version,
            "git_commit": self.git_commit,
            "scenarios": [sr.to_dict() for sr in self.scenario_results],
            "metadata": self.metadata,
        }


class BenchmarkRunner:
    """Executes benchmark scenarios against the compiled AIO graph."""

    SCENARIOS: Dict[str, str] = {
        "echo": "echo hello world",
        "safety_block": "kill the process and rm -rf /",
        "failure_recovery": "run bash command: not_a_real_command_12345",
        "context_overflow": "word " * 2000,
        "multi_agent": "write a python function to calculate fibonacci",
    }

    def __init__(
        self,
        benchmark_config: BenchmarkConfig,
        aio_config: Optional[AIOConfig] = None,
    ) -> None:
        self.bm_cfg = benchmark_config
        self.aio_cfg = aio_config or AIOConfig()
        # Use prometheus_port=0 to avoid port collisions in CI
        self.aio_cfg.observability.prometheus_port = 0
        self._collector: Optional[BenchmarkCollector] = None
        self._app: Any = None

    def _build_graph(self) -> Any:
        obs = ObservabilityLayer(self.aio_cfg.observability)
        self._collector = BenchmarkCollector(
            obs, enable_memory=self.bm_cfg.enable_memory_profiling
        )
        self._collector.install()
        return build_aio_graph(self.aio_cfg, observability_layer=obs)

    def run(self) -> BenchmarkResult:
        import platform
        import subprocess

        if self._app is None:
            self._app = self._build_graph()

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        git_commit: Optional[str] = None
        try:
            git_commit = (
                subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True)
                .strip()
            )
        except Exception:
            pass

        scenario_results: List[ScenarioResult] = []
        for scenario_name in self.bm_cfg.scenarios:
            input_text = self.SCENARIOS.get(scenario_name, scenario_name)
            result = self._run_scenario(scenario_name, input_text)
            scenario_results.append(result)

        return BenchmarkResult(
            timestamp=timestamp,
            python_version=platform.python_version(),
            git_commit=git_commit,
            scenario_results=scenario_results,
            metadata={
                "benchmark_config": self.bm_cfg.model_dump(),
                "aio_config": self.aio_cfg.model_dump(),
            },
        )

    def _run_scenario(self, name: str, input_text: str) -> ScenarioResult:
        assert self._collector is not None
        assert self._app is not None

        # Warmup
        for _ in range(self.bm_cfg.warmup_iterations):
            state = make_initial_state(input_text)
            self._app.invoke(state)

        self._collector.reset()

        # Measured iterations
        for _ in range(self.bm_cfg.iterations):
            state = make_initial_state(input_text)
            self._collector.sample_memory()
            start = time.perf_counter()
            self._app.invoke(state)
            elapsed = time.perf_counter() - start
            self._collector.record_e2e(elapsed)
            self._collector.sample_memory()

        snapshot = self._collector.snapshot()
        return ScenarioResult(
            name=name,
            snapshot=snapshot,
            input_text=input_text,
            iterations=self.bm_cfg.iterations,
            warmup_iterations=self.bm_cfg.warmup_iterations,
        )
