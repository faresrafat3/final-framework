from __future__ import annotations

import json
import logging
import subprocess
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..config.deps import HTTPX_AVAILABLE
from ..config.models import MCPConfig, MCPServerConfig
from .observability import ObservabilityLayer
from ..state import AIOState

if HTTPX_AVAILABLE:
    import httpx


class MCPTransport(ABC):
    """Abstract base for MCP JSON-RPC transports."""

    @abstractmethod
    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class StdioTransport(MCPTransport):
    """JSON-RPC over stdio using a subprocess."""

    def __init__(self, command: str, args: List[str], timeout: int = 30) -> None:
        self.command = command
        self.args = args
        self.timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._start()

    def _start(self) -> None:
        try:
            self._process = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to start MCP stdio server: {exc}") from exc

    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("MCP stdio process is not running")
        assert self._process.stdin is not None
        assert self._process.stdout is not None
        payload = json.dumps(message) + "\n"
        self._process.stdin.write(payload)
        self._process.stdin.flush()
        try:
            line = self._process.stdout.readline()
            if not line:
                raise RuntimeError("MCP stdio server closed stdout")
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON from MCP stdio server: {exc}") from exc

    def close(self) -> None:
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            self._process = None


class SSETransport(MCPTransport):
    """JSON-RPC over Server-Sent Events via HTTP."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> None:
        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx is required for SSE transport")
        self.url = url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self._client: Optional[Any] = None
        self._connect()

    def _connect(self) -> None:
        self._client = httpx.Client(headers=self.headers, timeout=self.timeout)

    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        if self._client is None:
            raise RuntimeError("SSE client is not connected")
        resp = self._client.post(
            f"{self.url}/message",
            json=message,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


class MCPClient:
    """JSON-RPC 2.0 client for the Model Context Protocol."""

    def __init__(self, config: MCPConfig, observability: ObservabilityLayer) -> None:
        self.config = config
        self.obs = observability
        self._transports: List[Tuple[str, MCPTransport]] = []
        self._available = False
        self._next_id = 1
        self._tool_registry: Dict[str, Tuple[str, MCPTransport]] = {}
        if not config.enable:
            self.obs.log(logging.INFO, "MCP disabled by configuration.")
            return
        self._initialize_transports()

    def _initialize_transports(self) -> None:
        for srv in self.config.servers:
            transport: Optional[MCPTransport] = None
            try:
                if srv.transport == "stdio":
                    if not srv.command:
                        raise ValueError("stdio transport requires 'command'")
                    transport = StdioTransport(
                        command=srv.command,
                        args=srv.args,
                        timeout=self.config.timeout_seconds,
                    )
                elif srv.transport == "sse":
                    if not HTTPX_AVAILABLE:
                        self.obs.log(logging.WARNING, f"httpx unavailable; skipping SSE MCP server '{srv.name}'")
                        continue
                    if not srv.url:
                        raise ValueError("sse transport requires 'url'")
                    transport = SSETransport(
                        url=srv.url,
                        headers=srv.headers,
                        timeout=self.config.timeout_seconds,
                    )
                else:
                    self.obs.log(logging.WARNING, f"Unknown MCP transport '{srv.transport}' for server '{srv.name}'")
                    continue
            except Exception as exc:
                self.obs.log(logging.WARNING, f"MCP transport init failed for '{srv.name}': {exc}")
                continue

            try:
                with self.obs.start_span("mcp.initialize"):
                    init_req = self._build_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "aio-mcp-client", "version": "1.0.0"}})
                    resp = transport.send(init_req)
                    if resp.get("error"):
                        self.obs.log(logging.WARNING, f"MCP initialize failed for '{srv.name}': {resp['error']}")
                        transport.close()
                        continue
            except Exception as exc:
                self.obs.log(logging.WARNING, f"MCP initialize exception for '{srv.name}': {exc}")
                transport.close()
                continue

            self._transports.append((srv.name, transport))
            self.obs.log(logging.INFO, f"MCP transport initialized for server '{srv.name}'")

        self._available = len(self._transports) > 0

    def _build_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        req_id = self._next_id
        self._next_id += 1
        return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}

    def list_tools(self) -> List[Dict[str, Any]]:
        tools: List[Dict[str, Any]] = []
        if not self._available:
            return tools
        with self.obs.start_span("mcp.list_tools"):
            for srv_name, transport in self._transports:
                try:
                    req = self._build_request("tools/list")
                    resp = transport.send(req)
                    if resp.get("error"):
                        self.obs.log(logging.WARNING, f"MCP tools/list error for '{srv_name}': {resp['error']}")
                        continue
                    result = resp.get("result", {})
                    srv_tools = result.get("tools", [])
                    for t in srv_tools:
                        t["_mcp_server"] = srv_name
                    tools.extend(srv_tools)
                except Exception as exc:
                    self.obs.log(logging.WARNING, f"MCP tools/list exception for '{srv_name}': {exc}")
            self.obs.count_node("mcp.list_tools", "success" if tools else "failure")
        return tools

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return {"success": False, "stdout": "", "stderr": "MCP not available", "exit_code": -1}
        transport = None
        for sn, tr in self._transports:
            if sn == server_name:
                transport = tr
                break
        if transport is None:
            return {"success": False, "stdout": "", "stderr": f"MCP server '{server_name}' not found", "exit_code": -1}
        start = time.time()
        with self.obs.start_span("mcp.call_tool"):
            try:
                req = self._build_request("tools/call", {"name": tool_name, "arguments": arguments})
                resp = transport.send(req)
                if resp.get("error"):
                    err = resp["error"]
                    self.obs.count_node("mcp.call_tool", "failure")
                    return {"success": False, "stdout": "", "stderr": f"MCP error: {err}", "exit_code": -1}
                result = resp.get("result", {})
                content = result.get("content", [])
                text_parts = [c["text"] for c in content if c.get("type") == "text"]
                stdout = "\n".join(text_parts)
                self.obs.record_latency("mcp.call_tool", time.time() - start)
                self.obs.count_node("mcp.call_tool", "success")
                return {"success": True, "stdout": stdout, "stderr": "", "exit_code": 0}
            except Exception as exc:
                self.obs.record_latency("mcp.call_tool", time.time() - start)
                self.obs.count_node("mcp.call_tool", "failure")
                return {"success": False, "stdout": "", "stderr": f"MCP exception: {exc}", "exit_code": -1}

    def discover_and_register(self, toolgate: Any) -> List[str]:
        discovered: List[str] = []
        if not self._available or not self.config.auto_discover:
            return discovered
        tools = self.list_tools()
        for tool in tools:
            name = tool.get("name", "unknown")
            server = tool.get("_mcp_server", "unknown")
            prefixed_name = f"mcp/{server}/{name}"
            schema = tool.get("inputSchema", {"type": "object"})
            self._tool_registry[prefixed_name] = (server, name)

            def _make_handler(sn: str, tn: str) -> Callable[..., Any]:
                def handler(**kwargs: Any) -> str:
                    result = self.call_tool(sn, tn, kwargs)
                    if not result.get("success"):
                        raise RuntimeError(result.get("stderr", "MCP tool failed"))
                    return result.get("stdout", "")
                return handler

            toolgate.register_tool(
                name=prefixed_name,
                schema=schema,
                sandbox=False,
                timeout=self.config.timeout_seconds,
                handler=_make_handler(server, name),
            )
            discovered.append(prefixed_name)
            self.obs.log(logging.INFO, f"Registered MCP tool: {prefixed_name}")
        return discovered

    def is_available(self) -> bool:
        return self._available

    def close(self) -> None:
        for _, transport in self._transports:
            transport.close()
        self._transports.clear()
        self._available = False


def node_mcp_discover(state: AIOState, mcp_client: MCPClient, toolgate: Any) -> AIOState:
    """Node wrapper for dynamic MCP discovery."""
    if not mcp_client.is_available():
        state["mcp_discovered_tools"] = state.get("mcp_discovered_tools") or []
        return state
    discovered = mcp_client.discover_and_register(toolgate)
    existing = state.get("mcp_discovered_tools") or []
    state["mcp_discovered_tools"] = existing + discovered
    return state
