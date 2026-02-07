#!/bin/bash
# Run the AI Chat CLI inside the running ai-analyst container
# Usage: ./services/ai-analyst/scripts/chat.sh

if [ ! -f "docker-compose.yml" ]; then
    echo "Error: Please run this script from the project root (where docker-compose.yml is located)."
    exit 1
fi

echo "Starting AI Chat CLI..."
docker compose exec ai-analyst python3 scripts/chat_cli.py "$@"
