#!/bin/bash
set -e

echo "Building Olympus Predictor Service..."
docker compose build olympus-predictor

echo "Running Verification Tests inside Container..."
docker compose run --rm olympus-predictor pytest tests/test_model.py -v

echo "Verification Complete!"
