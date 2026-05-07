from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .store import AuditStore


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_templates: Jinja2Templates | None = None


def _get_templates() -> Jinja2Templates:
    global _templates  # noqa: PLW0603
    if _templates is None:
        _templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
    return _templates


def create_dashboard_app(store: AuditStore, streaming_manager: Optional[Any] = None) -> FastAPI:
    """Build and return a FastAPI application wired to *store*.

    Args:
        store: Audit store for governance data.
        streaming_manager: Optional :class:`aio.streaming.StreamingManager`.
            When provided, a ``/ws/live`` WebSocket endpoint is exposed that
            streams real-time layer activity.
    """
    app = FastAPI(
        title="AIO Governance Dashboard",
        description="View audit trails and compliance violations from the SafetyGovernance layer.",
    )
    templates = _get_templates()

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Any:
        summary = store.summary()
        sessions = store.get_sessions()
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "summary": summary,
                "sessions": sessions,
            },
        )

    @app.get("/session/{session_id}", response_class=HTMLResponse)
    def session_detail(request: Request, session_id: str) -> Any:
        audits = store.get_audit_trail(session_id)
        violations = store.get_violations(session_id)
        return templates.TemplateResponse(
            request=request,
            name="session.html",
            context={
                "session_id": session_id,
                "audits": audits,
                "violations": violations,
            },
        )

    @app.get("/api/summary")
    def api_summary() -> Dict[str, Any]:
        return store.summary()

    @app.get("/api/audits")
    def api_audits(session_id: str | None = None) -> List[Dict[str, Any]]:
        return store.get_audit_trail(session_id)

    @app.get("/api/violations")
    def api_violations(session_id: str | None = None) -> List[Dict[str, Any]]:
        return store.get_violations(session_id)

    if streaming_manager is not None:
        @app.websocket("/ws/live")
        async def ws_live(websocket: WebSocket) -> None:
            await websocket.accept()
            try:
                while True:
                    events = streaming_manager.get_buffer()
                    if events:
                        await websocket.send_text(
                            json.dumps({"events": events}, default=str)
                        )
                    await asyncio.sleep(0.5)
            except Exception:
                pass
            finally:
                try:
                    await websocket.close()
                except Exception:
                    pass

    return app
