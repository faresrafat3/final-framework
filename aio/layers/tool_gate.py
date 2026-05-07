from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable, Dict, Optional

from ..config.deps import DOCKER_AVAILABLE
from ..config.models import ToolGateConfig
from .observability import ObservabilityLayer
from ..state import AIOState

if DOCKER_AVAILABLE:
    import docker


class ToolGate:
    """Layer 7 — Capability registry, HermesAgent routing, and Docker sandbox execution.

    Args:
        config: Layer 7 configuration (socket, timeouts, sandbox limits).
        observability: Shared observability layer for spans and metrics.
        mcp_client: Optional :class:`aio.layers.mcp_client.MCPClient` for dynamic tool discovery.
    """

    def __init__(self, config: ToolGateConfig, observability: ObservabilityLayer, mcp_client: Optional[Any] = None) -> None:
        self.config = config
        self.obs = observability
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._docker_client: Optional[Any] = None
        self._mcp_client = mcp_client
        if DOCKER_AVAILABLE:
            try:
                self._docker_client = docker.DockerClient(base_url=config.docker_socket)
                self.obs.log(logging.INFO, "Docker client initialized.")
            except Exception as exc:
                self.obs.log(logging.WARNING, f"Docker client init failed: {exc}")
        self._register_defaults()
        if self._mcp_client is not None:
            try:
                self._mcp_client.discover_and_register(self)
            except Exception as exc:
                self.obs.log(logging.WARNING, f"MCP discovery failed: {exc}")

    def _register_defaults(self) -> None:
        """Register the built-in python, bash, and echo tools."""
        self.register_tool(
            name="python_sandbox",
            schema={"type": "object", "properties": {"code": {"type": "string"}}},
            sandbox=True,
            timeout=self.config.default_timeout_seconds,
        )
        self.register_tool(
            name="bash_sandbox",
            schema={"type": "object", "properties": {"command": {"type": "string"}}},
            sandbox=True,
            timeout=self.config.default_timeout_seconds,
        )
        self.register_tool(
            name="echo",
            schema={"type": "object", "properties": {"message": {"type": "string"}}},
            sandbox=False,
            timeout=5,
        )

    def register_tool(
        self,
        name: str,
        schema: Dict[str, Any],
        sandbox: bool = True,
        timeout: int = 30,
        handler: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Add a new tool to the capability registry.

        Args:
            name: Unique tool identifier.
            schema: JSON-schema describing expected parameters.
            sandbox: Whether to run inside a Docker container.
            timeout: Max execution seconds.
            handler: Optional Python callable for non-sandbox tools.
        """
        self._registry[name] = {
            "name": name,
            "schema": schema,
            "sandbox": sandbox,
            "timeout": timeout,
            "handler": handler,
        }
        self.obs.log(logging.INFO, f"Tool registered: {name}")

    def route(self, state: AIOState) -> str:
        """Select the most appropriate tool for the current intent/plan.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Tool name (``python_sandbox``, ``bash_sandbox``, or ``echo``).
        """
        intent = state.get("intent") or "general"
        plan = state.get("plan") or ""
        lowered = (intent + " " + plan).lower()
        if "code" in lowered or "python" in lowered:
            return "python_sandbox"
        if "run" in lowered or "bash" in lowered or "command" in lowered:
            return "bash_sandbox"
        return "echo"

    def execute(self, state: AIOState) -> AIOState:
        """Route, parameterise, and run the selected tool.

        Args:
            state: Current :class:`AIOState`.

        Returns:
            Mutated state with ``execution_result`` and optionally ``mcp_execution_metadata``.
        """
        start = time.time()
        with self.obs.start_span("toolgate.execute", state.get("trace_id")):
            tool_name = self.route(state)
            tool = self._registry.get(tool_name)
            if not tool:
                state["execution_result"] = {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Unknown tool: {tool_name}",
                    "exit_code": -1,
                    "tool": tool_name,
                }
                self.obs.count_node("toolgate.execute", "failure")
                return state

            params = self._extract_params(tool_name, state.get("plan", ""))
            result = {"tool": tool_name, "params": params}

            if tool["sandbox"]:
                result.update(self._docker_run(tool, params))
            else:
                result.update(self._direct_run(tool, params))

            state["execution_result"] = result
            if tool_name.startswith("mcp/") and self._mcp_client is not None:
                state["mcp_execution_metadata"] = {
                    "tool": tool_name,
                    "latency_ms": round((time.time() - start) * 1000, 2),
                }
            status = "success" if result.get("success") else "failure"
            self.obs.record_latency("toolgate.execute", time.time() - start)
            self.obs.count_node("toolgate.execute", status)
        return state

    def _extract_params(self, tool_name: str, plan: str) -> Dict[str, Any]:
        safe_plan = plan or ""
        if tool_name == "python_sandbox":
            m = re.search(r"```python\r?\n(.*?)```", safe_plan, re.S)
            if m:
                return {"code": m.group(1).strip("\n\r")}
            return {"code": (safe_plan or "print('hello')").strip("\n\r")}
        if tool_name == "bash_sandbox":
            m = re.search(r"```bash\r?\n(.*?)```", safe_plan, re.S)
            if m:
                return {"command": m.group(1).strip("\n\r")}
            return {"command": (safe_plan or "echo hello").strip("\n\r")}
        if tool_name == "echo":
            return {"message": (safe_plan or "echo").strip()}
        return {}

    def _docker_run(self, tool: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool inside a Docker sandbox.

        If ``self._docker_client`` is ``None`` or Docker is globally unavailable,
        returns a graceful failure so that tests can mock the client directly.

        Args:
            tool: Registry entry for the tool.
            params: Extracted parameters dict.

        Returns:
            Result dict with ``success``, ``stdout``, ``stderr``, ``exit_code``.
        """
        if self._docker_client is None or not DOCKER_AVAILABLE:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Docker not available",
                "exit_code": -1,
            }
        image = "python:3.12-slim" if tool["name"] == "python_sandbox" else "alpine:latest"
        if tool["name"] == "python_sandbox":
            cmd = ["python", "-c", params.get("code", "")]
        elif tool["name"] == "bash_sandbox":
            cmd = ["sh", "-c", params.get("command", "")]
        else:
            cmd = ["echo", str(params)]
        try:
            container = self._docker_client.containers.run(
                image,
                command=cmd,
                detach=True,
                mem_limit=f"{self.config.max_memory_mb}m",
                cpu_quota=self.config.cpu_quota,
                network_disabled=self.config.network_disabled,
                read_only=self.config.read_only_rootfs,
                remove=True,
            )
            try:
                exit_code = container.wait(timeout=tool["timeout"])["StatusCode"]
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            except Exception as wait_exc:
                container.kill()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Docker wait/timeout error: {wait_exc}",
                    "exit_code": -1,
                }
            return {
                "success": exit_code == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }
        except Exception as exc:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Docker execution error: {exc}",
                "exit_code": -1,
            }

    def _direct_run(self, tool: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a non-sandbox tool via its handler or built-in fallback.

        Args:
            tool: Registry entry for the tool.
            params: Extracted parameters dict.

        Returns:
            Result dict with ``success``, ``stdout``, ``stderr``, ``exit_code``.
        """
        handler = tool.get("handler")
        if handler:
            try:
                out = handler(**params)
                return {"success": True, "stdout": str(out), "stderr": "", "exit_code": 0}
            except Exception as exc:
                return {"success": False, "stdout": "", "stderr": str(exc), "exit_code": -1}
        if tool["name"] == "echo":
            msg = params.get("message", "")
            return {"success": True, "stdout": msg, "stderr": "", "exit_code": 0}
        return {"success": False, "stdout": "", "stderr": "No handler", "exit_code": -1}
