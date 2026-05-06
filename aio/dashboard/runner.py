from __future__ import annotations

import argparse
import os

from .store import AuditStore


def _enable_flag() -> bool:
    return os.getenv("GOVERNANCE_DASHBOARD_ENABLE", "false").lower() == "true"


def main() -> None:  # pragma: no cover
    if not _enable_flag():
        print("Governance Dashboard is disabled. Set GOVERNANCE_DASHBOARD_ENABLE=true to start.")
        raise SystemExit(1)

    parser = argparse.ArgumentParser(description="AIO Governance Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8050, help="Bind port (default: 8050)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    import uvicorn

    from .app import create_dashboard_app

    store = AuditStore()
    app = create_dashboard_app(store)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
