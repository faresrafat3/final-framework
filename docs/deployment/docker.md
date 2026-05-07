# Docker Deployment

The repository includes a multi-stage `Dockerfile` and a `docker-compose.yml` for local observability stacks.

## Multi-Stage Build

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder
# ... installs build deps and pip-installs aio-framework[all]

FROM python:3.12-slim AS runtime
# ... copies artifacts, exposes ports, sets healthcheck
```

## Build & Run

```bash
# Build the image
docker build -t aio-framework:latest .

# Run a single query
docker run -e OPENAI_API_KEY=$OPENAI_API_KEY aio-framework:latest run "echo hello world"

# Run with a custom config JSON
docker run -e AIO_CONFIG_JSON='{"context":{"max_tokens":2048}}' aio-framework:latest run "echo hello"
```

## Docker Compose

The included `docker-compose.yml` starts the observability stack:

```bash
docker-compose up -d
```

Services:

| Service | Port | Purpose |
|---------|------|---------|
| OTel Collector | `4317` (gRPC) | Trace and metric ingestion |
| Prometheus | `9090` | Time-series metrics |
| Grafana | `3000` | Dashboards and visualisation |
| Jaeger | `16686` | Distributed trace UI |

## Healthcheck

The Dockerfile includes a healthcheck:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import aio; print('ok')" || exit 1
```

## Exposed Ports

- `8000` — Governance dashboard (when started via `aio dashboard`)
- `9091` — Prometheus metrics endpoint (when enabled in config)
