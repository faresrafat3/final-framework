from unittest.mock import MagicMock, patch

import pytest

from aio_framework import (
    ToolGate,
    ToolGateConfig,
    ObservabilityLayer,
    ObservabilityConfig,
    make_initial_state,
)


@pytest.fixture
def toolgate():
    obs = ObservabilityLayer(ObservabilityConfig(log_level="DEBUG", prometheus_port=0))
    return ToolGate(ToolGateConfig(docker_socket="unix:///var/run/docker.sock"), obs)


class TestToolGate:
    def test_register_tool(self, toolgate):
        toolgate.register_tool("custom", {"type": "object"}, sandbox=False, timeout=5)
        assert "custom" in toolgate._registry

    def test_default_registry_populated(self, toolgate):
        assert "python_sandbox" in toolgate._registry
        assert "bash_sandbox" in toolgate._registry
        assert "echo" in toolgate._registry

    def test_route_python(self, toolgate):
        state = make_initial_state("")
        state["intent"] = "coding"
        state["plan"] = "write some python code"
        assert toolgate.route(state) == "python_sandbox"

    def test_route_bash(self, toolgate):
        state = make_initial_state("")
        state["intent"] = "action"
        state["plan"] = "run bash command"
        assert toolgate.route(state) == "bash_sandbox"

    def test_route_echo_fallback(self, toolgate):
        state = make_initial_state("")
        state["intent"] = "general"
        state["plan"] = "say hello"
        assert toolgate.route(state) == "echo"

    def test_extract_params_python_block(self, toolgate):
        plan = 'Some text\n```python\nprint(1)\n```\nend'
        params = toolgate._extract_params("python_sandbox", plan)
        assert params["code"].strip() == "print(1)"

    def test_extract_params_bash_block(self, toolgate):
        plan = 'Run:\n```bash\necho hi\n```'
        params = toolgate._extract_params("bash_sandbox", plan)
        assert params["command"].strip() == "echo hi"

    def test_execute_unknown_tool(self, toolgate):
        with patch.object(toolgate, "route", return_value="missing"):
            state = make_initial_state("")
            state = toolgate.execute(state)
        assert state["execution_result"]["success"] is False
        assert "Unknown tool" in state["execution_result"]["stderr"]

    def test_direct_run_echo(self, toolgate):
        state = make_initial_state("")
        state["plan"] = "hello"
        state = toolgate.execute(state)
        assert state["execution_result"]["success"] is True
        assert state["execution_result"]["stdout"] == "hello"

    def test_docker_run_not_available(self, toolgate):
        with patch("aio_framework.DOCKER_AVAILABLE", False):
            result = toolgate._docker_run(toolgate._registry["python_sandbox"], {"code": "print(1)"})
        assert result["success"] is False
        assert "Docker not available" in result["stderr"]

    def test_docker_run_mock_success(self, toolgate):
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [
            b"stdout content",
            b"stderr content",
        ]
        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container
        toolgate._docker_client = mock_client
        result = toolgate._docker_run(toolgate._registry["python_sandbox"], {"code": "print(1)"})
        assert result["success"] is True
        assert result["stdout"] == "stdout content"
        assert result["stderr"] == "stderr content"
        assert result["exit_code"] == 0

    def test_docker_run_mock_failure_exit_code(self, toolgate):
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.side_effect = [b"", b"error"]
        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container
        toolgate._docker_client = mock_client
        result = toolgate._docker_run(toolgate._registry["bash_sandbox"], {"command": "false"})
        assert result["success"] is False
        assert result["exit_code"] == 1
