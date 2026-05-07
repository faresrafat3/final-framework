from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

from ..config.deps import JINJA2_AVAILABLE
from .runner import BenchmarkResult


class JSONReporter:
    """Serializes a BenchmarkResult to JSON."""

    def report(self, result: BenchmarkResult, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"benchmark_{result.timestamp.replace(':', '-')}.json"
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(result.to_dict(), fh, indent=2, default=str)
        return path


class HTMLReporter:
    """Emits an HTML report with tables and inline SVG bar charts.

    Uses Jinja2 if available; otherwise generates minimal plain HTML.
    """

    def report(self, result: BenchmarkResult, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"benchmark_{result.timestamp.replace(':', '-')}.html"
        path = os.path.join(output_dir, filename)
        html = self._render(result)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        return path

    def _render(self, result: BenchmarkResult) -> str:
        if JINJA2_AVAILABLE:
            import jinja2 as _jinja2

            template = _jinja2.Template(self._JINJA_TEMPLATE)
            return template.render(result=result, scenarios=result.scenario_results)
        return self._plain_html(result)

    def _plain_html(self, result: BenchmarkResult) -> str:
        lines = [
            "<!DOCTYPE html>",
            "<html><head><meta charset='utf-8'><title>AIO Benchmark Report</title>",
            "<style>body{font-family:sans-serif;margin:2rem;}table{border-collapse:collapse;width:100%;}th,td{border:1px solid #ccc;padding:8px;text-align:left;}th{background:#f0f0f0;}h2{margin-top:2rem;}</style>",
            "</head><body>",
            f"<h1>AIO Benchmark Report</h1>",
            f"<p>Timestamp: {result.timestamp}</p>",
            f"<p>Python: {result.python_version}</p>",
            f"<p>Git: {result.git_commit or 'N/A'}</p>",
        ]
        for sr in result.scenario_results:
            lines.append(f"<h2>Scenario: {sr.name}</h2>")
            lines.append("<table>")
            lines.append("<tr><th>Metric</th><th>Value</th></tr>")
            lines.append(f"<tr><td>E2E p50 (s)</td><td>{sr.e2e_p50:.6f}</td></tr>")
            lines.append(f"<tr><td>E2E p99 (s)</td><td>{sr.e2e_p99:.6f}</td></tr>")
            lines.append(f"<tr><td>E2E mean (s)</td><td>{sr.e2e_mean:.6f}</td></tr>")
            lines.append(f"<tr><td>Throughput (inv/s)</td><td>{sr.throughput:.2f}</td></tr>")
            lines.append("</table>")
            if sr.snapshot.node_snapshots:
                lines.append("<h3>Per-Node Latency</h3>")
                lines.append("<table>")
                lines.append("<tr><th>Node</th><th>p50 (s)</th><th>p99 (s)</th><th>Mean (s)</th><th>Count</th></tr>")
                for node_name, ns in sr.snapshot.node_snapshots.items():
                    lines.append(
                        f"<tr><td>{node_name}</td><td>{ns.p50:.6f}</td><td>{ns.p99:.6f}</td><td>{ns.mean:.6f}</td><td>{ns.count}</td></tr>"
                    )
                lines.append("</table>")
        lines.append("</body></html>")
        return "\n".join(lines)

    _JINJA_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AIO Benchmark Report</title>
<style>
body { font-family: sans-serif; margin: 2rem; }
table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
th { background: #f0f0f0; }
h2 { margin-top: 2rem; }
.bar { fill: #4a90d9; }
.bar-bg { fill: #e0e0e0; }
</style>
</head>
<body>
<h1>AIO Benchmark Report</h1>
<p><strong>Timestamp:</strong> {{ result.timestamp }}</p>
<p><strong>Python:</strong> {{ result.python_version }}</p>
<p><strong>Git:</strong> {{ result.git_commit or 'N/A' }}</p>
{% for sr in scenarios %}
<h2>Scenario: {{ sr.name }}</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>E2E p50 (s)</td><td>{{ "%.6f"|format(sr.e2e_p50) }}</td></tr>
<tr><td>E2E p99 (s)</td><td>{{ "%.6f"|format(sr.e2e_p99) }}</td></tr>
<tr><td>E2E mean (s)</td><td>{{ "%.6f"|format(sr.e2e_mean) }}</td></tr>
<tr><td>Throughput (inv/s)</td><td>{{ "%.2f"|format(sr.throughput) }}</td></tr>
</table>
{% if sr.snapshot.node_snapshots %}
<h3>Per-Node Latency</h3>
<table>
<tr><th>Node</th><th>p50 (s)</th><th>p99 (s)</th><th>Mean (s)</th><th>Count</th></tr>
{% for node_name, ns in sr.snapshot.node_snapshots.items() %}
<tr><td>{{ node_name }}</td><td>{{ "%.6f"|format(ns.p50) }}</td><td>{{ "%.6f"|format(ns.p99) }}</td><td>{{ "%.6f"|format(ns.mean) }}</td><td>{{ ns.count }}</td></tr>
{% endfor %}
</table>
{% set max_latency = sr.snapshot.node_snapshots.values()|map(attribute='p50')|max %}
{% if max_latency > 0 %}
<h3>Latency Distribution (p50)</h3>
<svg width="600" height="{{ 30 + sr.snapshot.node_snapshots|length * 24 }}">
{% for node_name, ns in sr.snapshot.node_snapshots.items() %}
{% set y = loop.index0 * 24 %}
{% set bar_width = (ns.p50 / max_latency) * 400 %}
<rect class="bar-bg" x="150" y="{{ y + 4 }}" width="400" height="16" />
<rect class="bar" x="150" y="{{ y + 4 }}" width="{{ bar_width }}" height="16" />
<text x="0" y="{{ y + 16 }}" font-size="12">{{ node_name[:30] }}</text>
<text x="560" y="{{ y + 16 }}" font-size="12">{{ "%.4f"|format(ns.p50) }}</text>
{% endfor %}
</svg>
{% endif %}
{% endif %}
{% endfor %}
</body>
</html>
"""
