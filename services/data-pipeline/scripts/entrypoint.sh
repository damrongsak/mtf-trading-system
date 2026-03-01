#!/bin/bash
set -e

echo "Running migrations for data-pipeline..."
# Run migrations using the pipeline-specific alembic.ini
alembic upgrade head

echo "Running dry-run startup check..."
python scripts/startup_check.py
if [ $? -ne 0 ]; then
    echo "Startup check FAILED. Exiting."
    exit 1
fi

echo "Starting data-pipeline service..."
# Exec into uvicorn
exec "$@"
