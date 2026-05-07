# Configuration

All behaviour is driven by `AIOConfig` (Pydantic v2) and environment variables.

## Top-Level Config

```python
from aio import AIOConfig

config = AIOConfig()
```

`AIOConfig` is a hierarchical composition of every layer-specific config model. Each nested field can be overridden individually or via environment variables. The `enable_priority_3` flag acts as a master switch for Layers 9–12.

## Environment Variable Overrides

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | LLM provider key |
| `LANGCHAIN_API_KEY` | — | LangSmith tracking (optional) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OpenTelemetry collector |
| `PROMETHEUS_PORT` | `9090` | Metrics server port |
| `DOCKER_SOCKET_PATH` | `unix:///var/run/docker.sock` | Docker daemon socket |
| `MAX_RETRIES` | `3` | Failure recovery retry budget |
| `SAFETY_MODE` | `strict` | NeuroShield enforcement level |
| `ENABLE_PRIORITY_3` | `true` | Master switch for Layers 9–12 |
| `SELF_EVOLUTION_ENABLE` | `true` | Layer 9 enable |
| `MULTI_AGENT_ENABLE` | `true` | Layer 10 enable |
| `SAFETY_GOVERNANCE_ENABLE` | `true` | Layer 11 enable |
| `COGNITIVE_IMMUNE_ENABLE` | `true` | Layer 12 enable |
| `MCP_ENABLE` | `false` | Enable MCP client and dynamic tool discovery |
| `MCP_SERVERS` | `[]` | JSON array of MCP server configs |
| `MCP_TIMEOUT_SECONDS` | `30` | Timeout for MCP JSON-RPC requests |

## JSON Override Example

You can pass a JSON blob to the CLI:

```bash
aio run "echo hello" --config-json '{"context":{"max_tokens":2048}}'
```

Or construct it programmatically:

```python
from aio import AIOConfig

config = AIOConfig(
    context={"max_tokens": 2048, "budget_reserve": 256},
    memory={"backend_type": "redis", "redis_url": "redis://localhost:6379/0"},
    enable_priority_3=False,
)
```

## Layer-Specific Configs

Each layer has its own Pydantic model under `aio.config.models`:

- `ObservabilityConfig` — tracing, metrics, logging
- `ContextConfig` — token budgets, BAPO defaults
- `MemoryConfig` — backends, embeddings, TTLs
- `PlanningConfig` — planner depths, LLM settings
- `CuriosityConfig` — novelty thresholds, reward weights
- `VerifierConfig` — ensemble thresholds, formal flags
- `ToolOptimizerConfig` — G-STEP, HDPO, JTPRO settings
- `ToolGateConfig` — Docker socket, sandbox limits
- `FailureRecoveryConfig` — retries, backoff, safety mode
- `SelfEvolutionConfig` — analysis windows, auto-apply
- `MultiAgentConfig` — agent registry, consensus threshold
- `SafetyGovernanceConfig` — audit level, constitutional enforcement
- `CognitiveImmuneConfig` — anomaly thresholds, learning settings
- `MCPConfig` — servers, timeouts, auto-discover
- `BenchmarkConfig` — iterations, scenarios, regression threshold

See the [API Reference](api-reference.md) for full field documentation.
