FROM python:3.11-slim-bookworm

# Install uv via pip to avoid ghcr.io key issues
RUN pip install uv

# Install curl and top (procps)
RUN apt-get update && apt-get install -y curl procps

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=0

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Configure the virtual environment path
ENV UV_PROJECT_ENVIRONMENT="/venv"

# Install the project's dependencies using the lockfile and settings
# Copy configuration files
COPY --chown=trader:trader pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

ENV PATH="/venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]