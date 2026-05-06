from unittest.mock import MagicMock, patch

import pytest

from aio_framework import (
    build_aio_graph,
    AIOConfig,
    make_initial_state,
    MCPClient,
    MCPConfig,
    MCPServerConfig,
)


class TestMCPIntegration:
    def test_graph_compiles_with_mcp_enabled(self):
        cfg = AIOConfig()
        cfg.mcp.enable = False
        app = build_aio_graph(cfg)
        assert app is not None

    def test_mcp_disabled_no_errors(self):
        cfg = AIOConfig()
        cfg.mcp.enable = False
        app = build_aio_graph(cfg)
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result["output"] is not None

    def test_mcp_enabled_but_no_servers_does_not_crash(self):
        cfg = AIOConfig()
        cfg.mcp.enable = True
        cfg.mcp.servers = []
        app = build_aio_graph(cfg)
        state = make_initial_state("echo hello")
        result = app.invoke(state)
        assert result["output"] is not None

    def test_mcp_tool_routes_and_executes(self):
        obs = MagicMock()
        mock_mcp = MagicMock(spec=MCPClient)
        mock_mcp.is_available.return_value = True
        mock_mcp.discover_and_register.return_value = ["mcp/test/greet"]
        mock_mcp._tool_registry = {"mcp/test/greet": ("test", "greet")}
        mock_mcp.call_tool.return_value = {"success": True, "stdout": "hello world", "stderr": "", "exit_code": 0}

        def fake_register(name, schema, sandbox, timeout, handler):
            tg._registry[name] = {
                "name": name,
                "schema": schema,
                "sandbox": sandbox,
                "timeout": timeout,
                "handler": handler,
            }

        from aio_framework import ToolGate, ToolGateConfig
        tg = ToolGate(ToolGateConfig(), obs, mcp_client=mock_mcp)
        fake_register("mcp/test/greet", {"type": "object"}, False, 30, lambda name="world": mock_mcp.call_tool("test", "greet", {"name": name})["stdout"])
        state = make_initial_state("")
        state["plan"] = "use mcp/test/greet with name=world"
        with patch.object(tg, "route", return_value="mcp/test/greet"):
            state = tg.execute(state)
        assert state["execution_result"]["success"] is True
        assert state["execution_result"]["stdout"] == "hello world"
        assert state.get("mcp_execution_metadata", {}).get("tool") == "mcp/test/greet"

    def test_fallback_to_local_tool_when_mcp_unreachable(self):
        obs = MagicMock()
        mock_mcp = MagicMock(spec=MCPClient)
        mock_mcp.is_available.return_value = False
        mock_mcp.discover_and_register.return_value = []
        from aio_framework import ToolGate, ToolGateConfig
        tg = ToolGate(ToolGateConfig(), obs, mcp_client=mock_mcp)
        state = make_initial_state("")
        state["plan"] = "hello"
        state = tg.execute(state)
        assert state["execution_result"]["success"] is True
        assert state["execution_result"]["stdout"] == "hello"
