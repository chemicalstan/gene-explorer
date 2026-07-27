FROM python:3.12-slim

# uv provides fast, reproducible installs from uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

WORKDIR /app

# Create a non-root user up front.
RUN useradd --system --uid 10001 appuser

# Install dependencies first (better layer caching), then the package. The venv
# is world-readable, so the non-root user can run it without owning the tree.
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8000

# Liveness probe for local runs. Kubernetes should use the HTTP probe directly.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", \
         "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/v1/health/live').status==200 else 1)"]

CMD ["uvicorn", "gene_explorer.asgi:build_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
