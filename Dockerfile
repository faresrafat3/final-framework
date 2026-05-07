# syntax=docker/dockerfile:1
# AIO Framework — Multi-stage production image

# ---------------------------------------------------------------------------
# Builder stage
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies (some wheels need compiling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging metadata first for layer caching
COPY pyproject.toml README.md CHANGELOG.md ./
COPY aio_framework.py ./
COPY aio/ ./aio/
COPY prompts/ ./prompts/

# Install the package with all extras into a dedicated prefix
RUN pip install --prefix=/install ".[all]"

# ---------------------------------------------------------------------------
# Runtime stage
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/app/bin:$PATH

WORKDIR /app

# Install only runtime libraries that have binary deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed site-packages and binaries from builder
COPY --from=builder /install /usr/local

# Copy application code (for editable-like imports and data files)
COPY aio/ ./aio/
COPY aio_framework.py ./
COPY prompts/ ./prompts/

# Ensure root-level module is importable
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Healthcheck: lightweight import smoke test
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import aio; print('ok')" || exit 1

EXPOSE 8000 9091

ENTRYPOINT ["aio"]
CMD ["run", "echo hello world"]
