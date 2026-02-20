FROM python:3.12-slim-bookworm

# Install uv via pip to avoid ghcr.io key issues (matching strategy-core style)
RUN pip install uv

# Create user first and prepare directory
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 trader && \
    mkdir -p /app && \
    chown trader:trader /app

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy
# Configure the virtual environment path
ENV UV_PROJECT_ENVIRONMENT="/venv"

# Copy configuration files
COPY --chown=trader:trader pyproject.toml ./

# Install dependencies
# Using --mount=type=cache to speed up re-builds
# Note: We don't have a uv.lock yet, so we just install from pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --prerelease=allow

# Copy application code
COPY --chown=trader:trader . .

ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH=/app

# Run the application with uvloop (handled by uvicorn[standard] or explicit policy)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]
