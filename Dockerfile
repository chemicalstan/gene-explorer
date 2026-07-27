# syntax=docker/dockerfile:1
FROM python:3.12-slim

# uv provides fast, reproducible installs from uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

WORKDIR /app

# Create a non-root user up front.
RUN useradd --system --uid 10001 appuser

# copy link mode avoids hardlink warnings across the cache mount; bytecode
# compile speeds container start.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# 1) Install dependencies only. This layer is cached and rebuilds solely when
#    pyproject.toml or uv.lock change, not when the source changes. The uv cache
#    mount persists downloaded wheels across builds.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 2) Install the project itself against the source.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# The venv is world-readable, so the non-root user runs it without owning the tree.
USER appuser
EXPOSE 8000

# Liveness probe for local runs. Kubernetes should use the HTTP probe directly.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", \
         "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/v1/health/live').status==200 else 1)"]

CMD ["uvicorn", "gene_explorer.asgi:build_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
