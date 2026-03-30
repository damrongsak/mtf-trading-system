# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Industrial Standard: Install directly into the final path to ensure correct shebangs
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-progress

# --- Stage 2: Runtime ---
FROM python:3.12-slim

# Install RUNTIME dependencies (curl preserved for healthchecks)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment and source code from builder
# Both stages now agree on /opt/venv
COPY --from=builder /opt/venv /opt/venv
# Copy uv into runtime so `uv run pytest` works inside exec sessions
COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv
COPY . .

# Environment configuration
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Production Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Industrial-Grade Execution: Gunicorn with Uvicorn Workers
# Using the module execution pattern for maximum stability
# Reduced workers and added --preload to optimize startup in constrained environments
CMD ["python", "-m", "gunicorn", "app.api.main:app", \
     "--workers", "1", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "300", \
     "--preload", \
     "--log-level", "info"]
