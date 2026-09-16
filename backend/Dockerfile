FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app

ENV UV_HTTP_TIMEOUT=300
# Copy only the dependency files first so this layer is cached
# and doesn't re-run on every code change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
