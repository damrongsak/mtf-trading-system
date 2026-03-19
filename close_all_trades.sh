#!/bin/bash

# Configuration
API_URL="http://localhost:8000"
USERNAME="${1:-demo1}"
PASSWORD="${2:-password123}"
SYMBOL="${3:-XAU_USD}"

echo "--- MTF Olympus Close All Trades Script ---"
echo "Target Account for User: $USERNAME (Symbol: ${SYMBOL:-ALL})"

# 1. Authenticate
echo "1. Authenticating..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=$USERNAME&password=$PASSWORD")

TOKEN=$(echo $LOGIN_RESPONSE | grep -oP '"access_token":"\K[^"]+')

if [ -z "$TOKEN" ]; then
    echo "   ❌ Authentication failed."
    echo "   Response: $LOGIN_RESPONSE"
    exit 1
fi
echo "   Success! Token acquired."

# 2. Get Broker Account ID
echo "2. Fetching Accounts..."
ACCOUNTS_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/accounts/" \
     -H "Authorization: Bearer $TOKEN")

# Pick the first cTrader account for demo1
ACCOUNT_ID=$(echo $ACCOUNTS_RESPONSE | grep -oP '"id":"\K[0-9a-f-]{36}' | head -n 1)

if [ -z "$ACCOUNT_ID" ]; then
    echo "   ❌ No broker accounts found."
    echo "   Response: $ACCOUNTS_RESPONSE"
    exit 1
fi
echo "   Selected Account ID: $ACCOUNT_ID"

# 3. Close All Trades
echo "3. Sending Close All Command..."
PAYLOAD="{\"broker_account_id\": \"$ACCOUNT_ID\""
if [ ! -z "$SYMBOL" ]; then
    PAYLOAD="$PAYLOAD, \"symbol\": \"$SYMBOL\""
fi
PAYLOAD="$PAYLOAD}"

CLOSE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/execution/trades/close-all" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d "$PAYLOAD")

if [[ "$CLOSE_RESPONSE" == *"success"* ]]; then
     echo "   ✅ Success! Command sent."
     echo "   Full Response: $CLOSE_RESPONSE"
else
    echo "   ❌ Failed."
    echo "   Response: $CLOSE_RESPONSE"
fi
