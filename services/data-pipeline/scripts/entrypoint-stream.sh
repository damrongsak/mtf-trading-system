#!/bin/bash
set -e

echo "Starting tick-streamer service (migrations handled by data-pipeline)..."
exec "$@"
