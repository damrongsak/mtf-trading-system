FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for numpy/pandas compilation if no wheels)
# Bookworm-slim is usually sufficient for wheels
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies into the system environment
RUN uv sync --no-install-project --no-dev

# Copy application code
COPY . .

# Install the project itself (if it's a package) or just rely on the venv
# Since we are running as a service, we can use 'uv run' which handles the venv
ENV PYTHONPATH=/app

# Create a non-root user
RUN useradd -m -u 1000 trader

# Change ownership of the app directory
RUN chown -R trader:trader /app

# Switch to the non-root user
USER trader

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
