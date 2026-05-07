from __future__ import annotations

import argparse
import json
import os
import sys

from ..config.models import BenchmarkConfig
from .regression import RegressionDetector
from .reporter import HTMLReporter, JSONReporter
from .runner import BenchmarkRunner


def _comma_split(val: str) -> list[str]:
    return [v.strip() for v in val.split(",") if v.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIO Framework Performance Benchmark Suite")
    parser.add_argument("--config", default=None, help="Path to optional config JSON/YAML (not implemented)")
    parser.add_argument("--scenarios", default=None, help="Comma-separated scenario names")
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--baseline", default=None, help="Path to baseline JSON for regression detection")
    parser.add_argument("--threshold", type=float, default=None, help="Regression threshold percent")
    parser.add_argument("--html", action="store_true", default=None, dest="html")
    parser.add_argument("--no-html", action="store_false", default=None, dest="html")
    parser.add_argument("--memory", action="store_true", default=None, dest="memory")
    parser.add_argument("--no-memory", action="store_false", default=None, dest="memory")
    args = parser.parse_args(argv)

    # Build BenchmarkConfig from CLI overrides
    kwargs: dict[str, object] = {}
    if args.iterations is not None:
        kwargs["iterations"] = args.iterations
    if args.warmup is not None:
        kwargs["warmup_iterations"] = args.warmup
    if args.scenarios is not None:
        kwargs["scenarios"] = _comma_split(args.scenarios)
    if args.output_dir is not None:
        kwargs["output_dir"] = args.output_dir
    if args.baseline is not None:
        kwargs["baseline_path"] = args.baseline
    if args.threshold is not None:
        kwargs["regression_threshold_percent"] = args.threshold
    if args.html is not None:
        kwargs["enable_html_report"] = args.html
    if args.memory is not None:
        kwargs["enable_memory_profiling"] = args.memory

    bm_cfg = BenchmarkConfig(**kwargs)
    runner = BenchmarkRunner(bm_cfg)
    result = runner.run()

    json_path = JSONReporter().report(result, bm_cfg.output_dir)
    print(f"JSON report: {json_path}")

    if bm_cfg.enable_html_report:
        html_path = HTMLReporter().report(result, bm_cfg.output_dir)
        print(f"HTML report: {html_path}")

    print("\nBenchmark Summary")
    print("=" * 50)
    for sr in result.scenario_results:
        print(f"Scenario: {sr.name}")
        print(f"  E2E p50: {sr.e2e_p50:.6f}s  p99: {sr.e2e_p99:.6f}s  mean: {sr.e2e_mean:.6f}s")
        print(f"  Throughput: {sr.throughput:.2f} inv/s")
        if sr.snapshot.memory_samples_bytes:
            mem_mb = [m / (1024 * 1024) for m in sr.snapshot.memory_samples_bytes]
            print(f"  Memory samples (MB): min={min(mem_mb):.2f} max={max(mem_mb):.2f}")

    if bm_cfg.baseline_path and os.path.exists(bm_cfg.baseline_path):
        detector = RegressionDetector(threshold_percent=bm_cfg.regression_threshold_percent)
        report = detector.compare(result, bm_cfg.baseline_path)
        print("\nRegression Detection")
        print("=" * 50)
        if report.passed:
            print("PASSED — no regressions detected.")
        else:
            print(f"FAILED — {len(report.regressions)} regression(s) detected:")
            for r in report.regressions:
                print(f"  {r.scenario}/{r.metric}: {r.baseline:.6f} -> {r.current:.6f} ({r.delta_percent:+.1f}%)")
        return 0 if report.passed else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
