FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_HTTP_TIMEOUT=300

# Create user first and prepare directory
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 trader && \
    mkdir -p /app && \
    chown trader:trader /app

WORKDIR /app

# Switch to user for all subsequent operations
USER trader

# Copy configuration files with correct ownership
COPY --chown=trader:trader pyproject.toml .
# COPY --chown=trader:trader uv.lock .

# Install dependencies into the user-owned environment
RUN uv sync --no-install-project --prerelease=allow

# Copy application code with correct ownership
COPY --chown=trader:trader . .

# Set environment variables
ENV PYTHONPATH=/app

# Run the application
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
