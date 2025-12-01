#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Starting API Health Checks..."
echo "-----------------------------"

check_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}

    echo -n "Checking $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    if [ "$response" -eq "$expected_status" ]; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC} (Status: $response)"
    fi
}

# 1. Health Checks
check_endpoint "API Gateway Health" "http://localhost/api/v1/health"
check_endpoint "Execution Service Health" "http://localhost/api/v1/execution/health"
check_endpoint "AI Analyst Health" "http://localhost/api/v1/ai-analyst/health"

echo ""
echo "Testing Signal Operations..."
echo "-----------------------------"

# 2. Signal Checks
echo -n "Fetching Latest Signal (XAUUSD)... "
signal_response=$(curl -s "http://localhost/api/v1/signal/latest/XAUUSD")
if [[ $signal_response == *"symbol"* ]]; then
     echo -e "${GREEN}PASS${NC}"
else
     echo -e "${RED}FAIL${NC}"
     echo "Response: $signal_response"
fi

echo -n "Triggering Manual Check (XAUUSD)... "
check_response=$(curl -s -X POST "http://localhost/api/v1/signal/check?symbol=XAUUSD")
if [[ $check_response == *"symbol"* ]]; then
     echo -e "${GREEN}PASS${NC}"
else
     echo -e "${RED}FAIL${NC}"
     echo "Response: $check_response"
fi

echo ""
echo "Done."
