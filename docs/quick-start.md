# Quick Start

## Installation

Install the package with all optional extras (recommended):

```bash
pip install aio-framework[all]
```

Or install in editable mode for development:

```bash
pip install -e ".[dev]"
```

## Configure Environment

Copy the example environment file and fill in your keys:

```bash
cp .env.example .env
```

Key variables:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | LLM provider key (required for LLM planning) |
| `LANGCHAIN_API_KEY` | LangSmith tracking (optional) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint |
| `ENABLE_PRIORITY_3` | Master switch for Layers 9–12 |

## Run a Single Query

```bash
aio run "echo hello world"
```

Backward-compatible direct script execution still works:

```bash
python aio_framework.py "echo hello world"
```

## Run Tests

```bash
# All tests with coverage
pytest tests/ -v --cov=aio --cov-report=term-missing

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v
```

## Start the Observability Stack

```bash
docker-compose up -d
```

This brings up:

- OpenTelemetry Collector (gRPC on `4317`)
- Prometheus (on `9090`)
- Grafana (on `3000`)
- Jaeger (on `16686`)

## Start the Governance Dashboard

```bash
aio dashboard --port 8000
```

Open <http://localhost:8000> to view audit trails and compliance violations.

## Next Steps

- Learn how to tune behaviour in the [Configuration Guide](configuration.md)
- Explore the [13-Layer Architecture](architecture/13-layers.md)
- Read the [API Reference](api-reference.md)
