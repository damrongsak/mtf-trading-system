#!/bin/bash
# Example queries to ask the AI Analyst about positioning features

# Wait for service to be ready
echo "Waiting for AI Analyst to be ready..."
sleep 5

# Example 1: General Market State with Positioning
echo "=========================================="
echo "Example 1: General Market State Analysis"
echo "=========================================="
curl -s -X POST http://localhost:8000/api/v1/ai/agent/observer/run \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Analyze the current market state for XAUUSD. What does the institutional positioning tell us?"
  }' | jq -r '.report'

echo ""
echo ""

# Example 2: Specific Positioning Questions
echo "=========================================="
echo "Example 2: Specific Positioning Analysis"
echo "=========================================="
curl -s -X POST http://localhost:8000/api/v1/ai/agent/observer/run \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "For XAUUSD: What is the Put/Call ratio? Is the market Long Crowded or Short Crowded? Where is Max Pain?"
  }' | jq -r '.report'

echo ""
echo ""

# Example 3: Positioning + Price Action
echo "=========================================="
echo "Example 3: Positioning + Price Context"
echo "=========================================="
curl -s -X POST http://localhost:8000/api/v1/ai/agent/observer/run \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Analyze XAUUSD: How does the current price relate to Max Pain? What does the OI Skew indicate about market sentiment?"
  }' | jq -r '.report'

echo ""
echo ""

# Example 4: Trading Implications
echo "=========================================="
echo "Example 4: Trading Implications"
echo "=========================================="
curl -s -X POST http://localhost:8000/api/v1/ai/agent/observer/run \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Given the current crowding regime and Max Pain level for XAUUSD, what are the potential trading implications?"
  }' | jq -r '.report'
