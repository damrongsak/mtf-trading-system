#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"

echo "1. Authenticating..."
# Login to get token
LOGIN_RESP=$(curl -s -X POST "$BASE_URL/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=trader1&password=password123")

TOKEN=$(echo $LOGIN_RESP | jq -r '.auth.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo "Authentication Failed!"
    echo $LOGIN_RESP
    exit 1
fi
echo "Authenticated. Token acquired."

AUTH_HEADER="Authorization: Bearer $TOKEN"

echo "2. Fetching Data Sources..."
SOURCES=$(curl -s -X GET "$BASE_URL/data-sources" -H "$AUTH_HEADER")
echo $SOURCES | jq '.'

# Extract first OANDA source ID
SOURCE_ID=$(echo $SOURCES | jq -r '.data[] | select(.provider=="OANDA") | .id' | head -n 1)

if [ -z "$SOURCE_ID" ] || [ "$SOURCE_ID" == "null" ]; then
    echo "Error: No OANDA data source found."
    exit 1
fi

echo "--------------------------------"
echo "Target Source ID: $SOURCE_ID"
echo "--------------------------------"

echo "3. Fetching Symbols for Source $SOURCE_ID..."
curl -s -X GET "$BASE_URL/data-sources/$SOURCE_ID/symbols" -H "$AUTH_HEADER" | jq '.'

echo "--------------------------------"
echo "4. Triggering Backfill for XAU/USD (M1)..."
# Using XAU_USD as normalized symbol, logic in data_source.py just passes it. Service resolves it.
curl -s -X POST "$BASE_URL/data-sources/$SOURCE_ID/backfill" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "XAU_USD", "timeframe": "M1", "count": 10}' | jq '.'

echo "--------------------------------"
echo "Done."
