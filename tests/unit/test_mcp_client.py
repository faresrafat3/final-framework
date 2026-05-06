from unittest.mock import MagicMock, patch

import pytest

from aio_framework import (
    MCPClient,
    MCPTransport,
    StdioTransport,
    SSETransport,
    MCPConfig,
    MCPServerConfig,
    ObservabilityLayer,
    ObservabilityConfig,
)


@pytest.fixture
def obs():
    return ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))


class TestMCPTransport:
    def test_stdio_transport_send_success(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.readline.return_value = '{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n'
        with patch("subprocess.Popen", return_value=mock_proc):
            transport = StdioTransport(command="echo", args=[])
            resp = transport.send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert resp["result"]["tools"] == []
        transport.close()

    def test_stdio_transport_process_not_running(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1
        with patch("subprocess.Popen", return_value=mock_proc):
            transport = StdioTransport(command="false", args=[])
        with pytest.raises(RuntimeError):
            transport.send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        transport.close()

    def test_sse_transport_send_success(self):
        with patch("aio.layers.mcp_client.HTTPX_AVAILABLE", True):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response
            with patch("httpx.Client", return_value=mock_client):
                transport = SSETransport(url="http://localhost:8080")
                resp = transport.send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            assert resp["result"]["tools"] == []
            transport.close()

    def test_sse_transport_requires_httpx(self):
        with patch("aio.layers.mcp_client.HTTPX_AVAILABLE", False):
            with pytest.raises(RuntimeError):
                SSETransport(url="http://localhost:8080")


class TestMCPClient:
    def test_client_disabled(self, obs):
        cfg = MCPConfig(enable=False)
        client = MCPClient(cfg, obs)
        assert not client.is_available()
        assert client.list_tools() == []

    def test_client_stdio_init_and_list_tools(self, obs):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        init_response = '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05"}}\n'
        list_response = '{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"read","inputSchema":{}}]}}\n'
        mock_proc.stdout.readline.side_effect = [init_response, list_response]
        with patch("subprocess.Popen", return_value=mock_proc):
            cfg = MCPConfig(
                enable=True,
                servers=[MCPServerConfig(name="test", transport="stdio", command="echo")],
                auto_discover=True,
            )
            client = MCPClient(cfg, obs)
        assert client.is_available()
        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "read"
        client.close()

    def test_call_tool_success(self, obs):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        init_response = '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05"}}\n'
        call_response = '{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"hi"}]}}\n'
        mock_proc.stdout.readline.side_effect = [init_response, call_response]
        with patch("subprocess.Popen", return_value=mock_proc):
            cfg = MCPConfig(
                enable=True,
                servers=[MCPServerConfig(name="test", transport="stdio", command="echo")],
            )
            client = MCPClient(cfg, obs)
        result = client.call_tool("test", "greet", {"name": "world"})
        assert result["success"] is True
        assert result["stdout"] == "hi"
        client.close()

    def test_call_tool_server_not_found(self, obs):
        cfg = MCPConfig(enable=True, servers=[])
        client = MCPClient(cfg, obs)
        result = client.call_tool("missing", "greet", {})
        assert result["success"] is False
        assert "not found" in result["stderr"]

    def test_discover_and_register(self, obs):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        init_response = '{"jsonrpc":"2.0","id":1,"result":{}}\n'
        list_response = '{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"add","inputSchema":{"type":"object"}}]}}\n'
        call_response = '{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"3"}]}}\n'
        mock_proc.stdout.readline.side_effect = [init_response, list_response, call_response]
        with patch("subprocess.Popen", return_value=mock_proc):
            cfg = MCPConfig(
                enable=True,
                servers=[MCPServerConfig(name="math", transport="stdio", command="echo")],
                auto_discover=True,
            )
            client = MCPClient(cfg, obs)
        mock_gate = MagicMock()
        discovered = client.discover_and_register(mock_gate)
        assert "mcp/math/add" in discovered
        mock_gate.register_tool.assert_called_once()
        args, kwargs = mock_gate.register_tool.call_args
        assert kwargs["name"] == "mcp/math/add"
        assert kwargs["sandbox"] is False
        handler = kwargs["handler"]
        out = handler(a=1, b=2)
        assert out == "3"
        client.close()

    def test_graceful_degradation_on_transport_failure(self, obs):
        with patch("subprocess.Popen", side_effect=RuntimeError("boom")):
            cfg = MCPConfig(
                enable=True,
                servers=[MCPServerConfig(name="bad", transport="stdio", command="false")],
            )
            client = MCPClient(cfg, obs)
        assert not client.is_available()
        assert client.list_tools() == []

    def test_observability_spans_called(self, obs):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        init_response = '{"jsonrpc":"2.0","id":1,"result":{}}\n'
        list_response = '{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}\n'
        mock_proc.stdout.readline.side_effect = [init_response, list_response]
        with patch.object(obs, "start_span") as mock_span, patch("subprocess.Popen", return_value=mock_proc):
            cfg = MCPConfig(
                enable=True,
                servers=[MCPServerConfig(name="test", transport="stdio", command="echo")],
            )
            client = MCPClient(cfg, obs)
            client.list_tools()
        assert mock_span.call_count >= 2
        names = [c.args[0] for c in mock_span.call_args_list]
        assert "mcp.initialize" in names
        assert "mcp.list_tools" in names
        client.close()
