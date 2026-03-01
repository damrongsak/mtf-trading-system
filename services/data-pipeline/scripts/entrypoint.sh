#!/bin/bash
set -e

echo "Running migrations for data-pipeline..."
# Run migrations using the pipeline-specific alembic.ini
alembic upgrade head

echo "Starting data-pipeline service..."
# Exec into uvicorn
exec "$@"
