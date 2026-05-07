"""AIO Framework CLI entrypoints.

Provides three subcommands:

* ``aio run`` – build the graph and invoke a single query.
* ``aio benchmark`` – delegate to the benchmark suite.
* ``aio dashboard`` – start the FastAPI governance dashboard.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence


def _cmd_run(argv: Sequence[str] | None = None) -> int:
    """Run a single query through the compiled AIO graph and print JSON output.

    Args:
        argv: Command-line tokens (defaults to ``sys.argv[1:]`` when *None*).

    Returns:
        Shell exit code (``0`` on success).
    """
    parser = argparse.ArgumentParser(description="Run the AIO framework on a single input.")
    parser.add_argument("query", nargs="?", default="echo hello world", help="Input query string")
    parser.add_argument("--session-id", default=None, help="Optional session identifier")
    parser.add_argument("--config-json", default=None, help="Optional JSON string to override AIOConfig")
    args = parser.parse_args(argv)

    from .config.models import AIOConfig
    from .graph.builder import build_aio_graph
    from .state import make_initial_state

    config: AIOConfig | None = None
    if args.config_json:
        import json as _json
        config = AIOConfig(**_json.loads(args.config_json))

    app = build_aio_graph(config)
    state = make_initial_state(args.query, args.session_id)
    result = app.invoke(state)
    # Strip internal metrics for readability
    out = {k: v for k, v in result.items() if k != "metrics"}
    print(json.dumps(out, indent=2, default=str))
    return 0


def _cmd_benchmark(argv: Sequence[str] | None = None) -> int:
    """Delegate to the benchmark suite CLI."""
    from .benchmark.cli import main as benchmark_main
    return benchmark_main(argv)


def _cmd_dashboard(argv: Sequence[str] | None = None) -> int:
    """Start the governance dashboard via Uvicorn.

    Args:
        argv: Command-line tokens parsed for ``--host``, ``--port``, ``--reload``.

    Returns:
        Shell exit code (``0``).  This function blocks while Uvicorn runs.
    """
    parser = argparse.ArgumentParser(description="Start the AIO Governance Dashboard.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except Exception as exc:  # pragma: no cover
        print("uvicorn is required for the dashboard. Install: pip install aio-framework[dashboard]")
        raise SystemExit(1) from exc

    try:
        from .dashboard.app import create_dashboard_app
        from .dashboard.store import AuditStore
    except Exception as exc:  # pragma: no cover
        print("Dashboard dependencies are missing. Install: pip install aio-framework[dashboard]")
        raise SystemExit(1) from exc

    store = AuditStore()
    app = create_dashboard_app(store)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """AIO Framework unified CLI dispatcher.

    Args:
        argv: Command-line tokens.  When *None* ``sys.argv[1:]`` is used.

    Returns:
        Shell exit code.
    """
    parser = argparse.ArgumentParser(prog="aio", description="AIO Framework CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Run a single query through the AIO graph")
    subparsers.add_parser("benchmark", help="Run the benchmark suite")
    subparsers.add_parser("dashboard", help="Start the governance dashboard")

    args, rest = parser.parse_known_args(argv)

    if args.command == "run":
        return _cmd_run(rest)
    if args.command == "benchmark":
        return _cmd_benchmark(rest)
    if args.command == "dashboard":
        return _cmd_dashboard(rest)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
