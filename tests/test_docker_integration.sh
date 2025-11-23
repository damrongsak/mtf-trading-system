#!/bin/bash

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Test Health Check
echo "Testing Execution Service Health..."
curl -s http://localhost:8001/health | grep "ok" || echo "Execution Service Health Check Failed"

# Test Risk Check via API Gateway
echo "Testing Risk Check via API Gateway..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/risk/check \
  -H "Content-Type: application/json" \
  -d '{
    "risk_usd": 10.0,
    "sl_distance_usd": 50.0,
    "min_lot": 0.01
  }')

echo "Response: $RESPONSE"

if echo "$RESPONSE" | grep -q '"can_execute":true'; then
  echo "Integration Test Passed!"
else
  echo "Integration Test Failed!"
  exit 1
fi
