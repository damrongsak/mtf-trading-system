#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000/api/v1"
USERNAME="trader1"
PASSWORD="password123"
TIMEFRAMES=("M1" "M5" "M15" "M30" "H1" "H4" "D" "W" "M")
COUNT=5000

echo "🚀 Starting Bulk Backfill Process..."

# 1. Authentication
echo "🔐 Authenticating..."
LOGIN_RESP=$(curl -s -X POST "$BASE_URL/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USERNAME&password=$PASSWORD")

TOKEN=$(echo $LOGIN_RESP | jq -r '.auth.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo "❌ Authentication Failed!"
    echo $LOGIN_RESP
    exit 1
fi
AUTH_HEADER="Authorization: Bearer $TOKEN"
echo "✅ Authenticated."

# 2. Get OANDA Data Source
echo "🔍 Finding OANDA Data Source..."
SOURCES=$(curl -s -X GET "$BASE_URL/data-sources" -H "$AUTH_HEADER")
SOURCE_ID=$(echo $SOURCES | jq -r '.data[] | select(.provider=="OANDA") | .id' | head -n 1)

if [ -z "$SOURCE_ID" ] || [ "$SOURCE_ID" == "null" ]; then
    echo "❌ No OANDA data source found."
    exit 1
fi
echo "✅ Found Source ID: $SOURCE_ID"

# 3. Fetch Symbols
echo "📥 Fetching Symbols list..."
SYMBOLS_JSON=$(curl -s -X GET "$BASE_URL/data-sources/$SOURCE_ID/symbols" -H "$AUTH_HEADER")
SYMBOLS=$(echo $SYMBOLS_JSON | jq -r '.data[]')
SYMBOL_COUNT=$(echo "$SYMBOLS" | wc -l)

echo "✅ Found $SYMBOL_COUNT symbols."
echo "---------------------------------------------------"
echo "⚠️  WARNING: This will trigger a massive amount of background jobs."
echo "   Requests: $SYMBOL_COUNT symbols * ${#TIMEFRAMES[@]} timeframes = $((SYMBOL_COUNT * ${#TIMEFRAMES[@]})) jobs."
echo "   Sleeping 0.1s between requests to be polite."
echo "---------------------------------------------------"
# Removed interactive read for automation
# read -r -p "Press ENTER to continue or Ctrl+C to cancel..."

# 4. Loop and Trigger
i=0
for SYMBOL in $SYMBOLS; do
    ((i++))
    echo "[$i/$SYMBOL_COUNT] Processing $SYMBOL..."
    
    for TF in "${TIMEFRAMES[@]}"; do
        # echo "   > Triggering $TF..."
        RESPONSE=$(curl -s -X POST "$BASE_URL/data-sources/$SOURCE_ID/backfill" \
          -H "$AUTH_HEADER" \
          -H "Content-Type: application/json" \
          -d "{\"symbol\": \"$SYMBOL\", \"timeframe\": \"$TF\", \"count\": $COUNT}")
          
        # Optional: Check for rate limit or error? 
        # echo $RESPONSE | jq -r '.message'
        
        # Micro-sleep to avoid flooding api-gateway event loop too hard
        # although FastAPI handles it, Oanda API rate limits might hit if valid immediately
        # Backfill service runs sequentially in background tasks? No, BackgroundTasks are async but Python GIL...
        # Also Oanda V20 client might rate limit.
        # sleep 0.1
    done
    # Sleep a bit more between symbols
    sleep 0.2
done

echo "✅ Bulk trigger complete."