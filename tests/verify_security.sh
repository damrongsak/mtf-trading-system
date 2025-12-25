#!/bin/bash
echo "---------------------------------------------------"
echo "TEST 1: Safe Code (Should Succeed)"
echo "---------------------------------------------------"
curl -s -X POST http://localhost:8000/api/v1/backtest/custom \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def strategy(data):\n    return data.close > data.open, data.close < data.open",
    "symbol": "XAU/USD",
    "timeframe": "1h",
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-01-05T00:00:00",
    "initial_capital": 10000,
    "fees": 0.0001,
    "slippage": 0.0001
}' | jq '.status'

echo -e "\n\n---------------------------------------------------"
echo "TEST 2: Unsafe Code - Import os (Should Fail)"
echo "---------------------------------------------------"
curl -s -X POST http://localhost:8000/api/v1/backtest/custom \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import os\ndef strategy(data):\n    print(os.environ)\n    return data.close > data.open, data.close < data.open",
    "symbol": "XAU/USD",
    "timeframe": "1h",
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-01-05T00:00:00",
    "initial_capital": 10000,
    "fees": 0.0001,
    "slippage": 0.0001
}' | jq '.status'

echo -e "\n\n---------------------------------------------------"
echo "TEST 3: Unsafe Code - __import__ (Should Fail)"
echo "---------------------------------------------------"
curl -s -X POST http://localhost:8000/api/v1/backtest/custom \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def strategy(data):\n    x = __import__(\"os\")\n    return data.close > data.open, data.close < data.open",
    "symbol": "XAU/USD",
    "timeframe": "1h",
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-01-05T00:00:00",
    "initial_capital": 10000,
    "fees": 0.0001,
    "slippage": 0.0001
}' | jq '.status'
