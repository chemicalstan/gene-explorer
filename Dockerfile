FROM python:3.12-slim

# uv provides fast, reproducible installs from uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (better layer caching), then the package.
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "gene_explorer.asgi:build_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
