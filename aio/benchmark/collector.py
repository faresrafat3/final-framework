from __future__ import annotations

import statistics
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..config.deps import PSUTIL_AVAILABLE
from ..layers.observability import ObservabilityLayer


@dataclass
class NodeSnapshot:
    latencies: List[float] = field(default_factory=list)
    statuses: List[str] = field(default_factory=list)
    memory_deltas_bytes: List[int] = field(default_factory=list)

    @property
    def p50(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.median(self.latencies)

    @property
    def p99(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        idx = max(0, min(idx, len(sorted_lat) - 1))
        return sorted_lat[idx]

    @property
    def mean(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.mean(self.latencies)

    @property
    def count(self) -> int:
        return len(self.latencies)

    def status_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for s in self.statuses:
            counts[s] = counts.get(s, 0) + 1
        return counts


@dataclass
class BenchmarkSnapshot:
    node_snapshots: Dict[str, NodeSnapshot] = field(default_factory=dict)
    e2e_times: List[float] = field(default_factory=list)
    memory_samples_bytes: List[int] = field(default_factory=list)
    throughput: float = 0.0
    iterations: int = 0

    @property
    def e2e_p50(self) -> float:
        if not self.e2e_times:
            return 0.0
        return statistics.median(self.e2e_times)

    @property
    def e2e_p99(self) -> float:
        if not self.e2e_times:
            return 0.0
        sorted_t = sorted(self.e2e_times)
        idx = int(len(sorted_t) * 0.99)
        idx = max(0, min(idx, len(sorted_t) - 1))
        return sorted_t[idx]

    @property
    def e2e_mean(self) -> float:
        if not self.e2e_times:
            return 0.0
        return statistics.mean(self.e2e_times)


class BenchmarkCollector:
    """Intercepts ObservabilityLayer metrics to accumulate benchmark data.

    Memory profiling uses ``psutil`` when available, falls back to
    ``tracemalloc`` (stdlib), otherwise skips silently.
    """

    def __init__(self, observability_layer: ObservabilityLayer, enable_memory: bool = True) -> None:
        self._obs = observability_layer
        self._enable_memory = enable_memory
        self._node_snapshots: Dict[str, NodeSnapshot] = {}
        self._e2e_times: List[float] = []
        self._memory_samples: List[int] = []
        self._original_record_latency = observability_layer.record_latency
        self._original_count_node = observability_layer.count_node
        self._process: Any = None
        self._tracemalloc_enabled = False

        if enable_memory:
            if PSUTIL_AVAILABLE:
                import psutil as _psutil

                self._process = _psutil.Process()
            else:
                if not tracemalloc.is_tracing():
                    tracemalloc.start()
                    self._tracemalloc_enabled = True

    def install(self) -> None:
        self._obs.record_latency = self._wrapped_record_latency
        self._obs.count_node = self._wrapped_count_node

    def uninstall(self) -> None:
        self._obs.record_latency = self._original_record_latency
        self._obs.count_node = self._original_count_node
        if self._tracemalloc_enabled:
            tracemalloc.stop()
            self._tracemalloc_enabled = False

    def _wrapped_record_latency(self, node_name: str, seconds: float) -> None:
        snap = self._node_snapshots.setdefault(node_name, NodeSnapshot())
        snap.latencies.append(seconds)
        return self._original_record_latency(node_name, seconds)

    def _wrapped_count_node(self, node_name: str, status: str) -> None:
        snap = self._node_snapshots.setdefault(node_name, NodeSnapshot())
        snap.statuses.append(status)
        return self._original_count_node(node_name, status)

    def record_e2e(self, seconds: float) -> None:
        self._e2e_times.append(seconds)

    def sample_memory(self) -> Optional[int]:
        if self._process is not None:
            try:
                rss = self._process.memory_info().rss
                self._memory_samples.append(rss)
                return rss
            except Exception:
                return None
        elif tracemalloc.is_tracing():
            current, _ = tracemalloc.get_traced_memory()
            self._memory_samples.append(current)
            return current
        return None

    def snapshot(self) -> BenchmarkSnapshot:
        throughput = 0.0
        if self._e2e_times:
            total = sum(self._e2e_times)
            if total > 0:
                throughput = len(self._e2e_times) / total
        return BenchmarkSnapshot(
            node_snapshots=dict(self._node_snapshots),
            e2e_times=list(self._e2e_times),
            memory_samples_bytes=list(self._memory_samples),
            throughput=throughput,
            iterations=len(self._e2e_times),
        )

    def reset(self) -> None:
        self._node_snapshots.clear()
        self._e2e_times.clear()
        self._memory_samples.clear()
