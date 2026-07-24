FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src ./src
RUN pip install --no-cache-dir .

CMD ["uvicorn", "gene_explorer.asgi:build_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
