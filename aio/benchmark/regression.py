from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .runner import BenchmarkResult, ScenarioResult


@dataclass
class RegressedMetric:
    scenario: str
    metric: str
    baseline: float
    current: float
    delta_percent: float


@dataclass
class RegressionReport:
    passed: bool
    threshold_percent: float
    regressions: List[RegressedMetric] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "threshold_percent": self.threshold_percent,
            "regressions": [
                {
                    "scenario": r.scenario,
                    "metric": r.metric,
                    "baseline": r.baseline,
                    "current": r.current,
                    "delta_percent": r.delta_percent,
                }
                for r in self.regressions
            ],
        }


class RegressionDetector:
    """Compares current benchmark results against a baseline JSON."""

    def __init__(self, threshold_percent: float = 10.0) -> None:
        self.threshold_percent = threshold_percent

    def compare(self, current: BenchmarkResult, baseline_path: str) -> RegressionReport:
        baseline = self._load_baseline(baseline_path)
        regressions: List[RegressedMetric] = []

        baseline_scenarios = {s["name"]: s for s in baseline.get("scenarios", [])}

        for sr in current.scenario_results:
            base = baseline_scenarios.get(sr.name)
            if base is None:
                continue

            # Compare e2e metrics
            for metric in ("e2e_p50", "e2e_p99", "e2e_mean"):
                base_val = float(base.get(metric, 0))
                cur_val = getattr(sr, metric, 0)
                if base_val > 0 and cur_val > base_val * (1 + self.threshold_percent / 100):
                    delta = ((cur_val - base_val) / base_val) * 100
                    regressions.append(
                        RegressedMetric(
                            scenario=sr.name,
                            metric=metric,
                            baseline=base_val,
                            current=cur_val,
                            delta_percent=delta,
                        )
                    )

            # Compare throughput (lower is worse)
            base_tput = float(base.get("throughput", 0))
            cur_tput = sr.throughput
            if base_tput > 0 and cur_tput < base_tput * (1 - self.threshold_percent / 100):
                delta = ((base_tput - cur_tput) / base_tput) * 100
                regressions.append(
                    RegressedMetric(
                        scenario=sr.name,
                        metric="throughput",
                        baseline=base_tput,
                        current=cur_tput,
                        delta_percent=delta,
                    )
                )

            # Compare per-node p50 and p99
            base_nodes = base.get("node_stats", {})
            cur_nodes = sr.snapshot.node_snapshots
            for node_name, ns in cur_nodes.items():
                bn = base_nodes.get(node_name)
                if not bn:
                    continue
                for metric in ("p50", "p99"):
                    base_val = float(bn.get(metric, 0))
                    cur_val = getattr(ns, metric, 0)
                    if base_val > 0 and cur_val > base_val * (1 + self.threshold_percent / 100):
                        delta = ((cur_val - base_val) / base_val) * 100
                        regressions.append(
                            RegressedMetric(
                                scenario=sr.name,
                                metric=f"{node_name}.{metric}",
                                baseline=base_val,
                                current=cur_val,
                                delta_percent=delta,
                            )
                        )

        return RegressionReport(
            passed=len(regressions) == 0,
            threshold_percent=self.threshold_percent,
            regressions=regressions,
        )

    def _load_baseline(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
