# Build context = repo ROOT (this is a uv workspace; the image needs packages/* + uv.lock).
#   docker build -f services/dashboard/Dockerfile .
FROM python:3.14-slim

# uv binary from its official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Workspace manifests + member sources (editable installs need the source present)
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
COPY services/ ./services/

RUN uv sync --frozen --no-dev --all-packages

EXPOSE 8003
CMD ["uv", "run", "--no-sync", "uvicorn", "dashboard.main:app", "--host", "0.0.0.0", "--port", "8003"]
