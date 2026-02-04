#!/bin/bash

# Configuration
API_URL="http://localhost:8000"
USERNAME="${1:-dan}"
PASSWORD="${2:-password}"
SIDE="${3:-BUY}"          # BUY / SELL
ORDER_TYPE="${4:-LIMIT}"  # LIMIT / MARKET / STOP
SYMBOL="${5:-XAU_USD}"
UNITS_RAW="${6:-1}"       # Positive units
PRICE="${7:-2000.0}"
SL_PRICE="${8:-1990.0}"
TP_PRICE="${9:-2020.0}"
COMMENT="${10}"

# Logic to sign units based on SIDE
if [ "$SIDE" == "SELL" ]; then
  UNITS="-$UNITS_RAW"
else
  UNITS="$UNITS_RAW"
fi

echo "--- MTF Olympus Limit Order Script ---"
echo "Target: $SYMBOL $SIDE $UNITS_RAW (Signed: $UNITS) @ $PRICE [$ORDER_TYPE]"

# 1. Authenticate
echo "1. Authenticating..."
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USERNAME&password=$PASSWORD")

# Extract Token
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['auth']['access_token'])" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Authentication failed."
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi
echo "   Success! Token acquired."

# 2. Get Account ID - Prioritizing cTrader
echo "2. Fetching Accounts..."
ACCOUNTS_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/accounts/" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

# Python script to find cTrader account, or fallback to first
ACCOUNT_DATA=$(echo "$ACCOUNTS_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)['data']
if not data:
    print('')
    sys.exit()

# Try to find CTRADER
target = next((a for a in data if a['broker_name'] == 'CTRADER'), None)

# Fallback to first if no cTrader
if not target:
    target = data[0]

print(f\"{target['id']}|{target['broker_name']}\")
" 2>/dev/null)

if [ -z "$ACCOUNT_DATA" ]; then
    echo "Error: No active broker accounts found."
    echo "Response: $ACCOUNTS_RESPONSE"
    exit 1
fi

ACCOUNT_ID=$(echo "$ACCOUNT_DATA" | cut -d'|' -f1)
BROKER_NAME=$(echo "$ACCOUNT_DATA" | cut -d'|' -f2)

echo "   Selected Account: $BROKER_NAME ($ACCOUNT_ID)"

# 3. Place Order
echo "3. Placing $ORDER_TYPE Order on $BROKER_NAME..."
ORDER_PAYLOAD=$(cat <<EOF
{
  "broker_account_id": "$ACCOUNT_ID",
  "symbol": "$SYMBOL",
  "order_type": "$ORDER_TYPE",
  "units": $UNITS,
  "price": $PRICE,
  "sl_price": $SL_PRICE,
  "tp_price": $TP_PRICE,
  "comment": "$COMMENT"
}
EOF
)

ORDER_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/execution/orders" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$ORDER_PAYLOAD")

# Check result
# API Gateway wraps response in {"status":"success", "data": {...}}
ORDER_ID=$(echo "$ORDER_RESPONSE" | python3 -c "import sys, json; resp=json.load(sys.stdin); print(resp.get('data', {}).get('id', ''))" 2>/dev/null)
MESSAGE=$(echo "$ORDER_RESPONSE" | python3 -c "import sys, json; resp=json.load(sys.stdin); print(resp.get('message', ''))" 2>/dev/null)

if [ -n "$ORDER_ID" ] && [ "$ORDER_ID" != "0" ]; then
    echo "   ✅ Success! Order Placed."
    echo "   Order ID: $ORDER_ID"
    echo "   Full Response: $ORDER_RESPONSE"
elif [ "$ORDER_ID" == "0" ] && [[ "$MESSAGE" == *"success"* || "$ORDER_RESPONSE" == *"success"* ]]; then
     echo "   ✅ Success! (Pending/Accepted)."
     echo "   Full Response: $ORDER_RESPONSE"
else
    echo "   ❌ Failed."
    echo "   Response: $ORDER_RESPONSE"
fi
