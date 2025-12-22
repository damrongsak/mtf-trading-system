#!/bin/bash

# Configuration
API_URL="http://localhost:8000/api/v1"
USERNAME="trader1"
PASSWORD="password123"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Multi-Broker Integration Test${NC}"

# 1. Login
echo -n "Logging in... "
LOGIN_RESP=$(curl -s -X POST "$API_URL/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USERNAME&password=$PASSWORD")

TOKEN=$(echo $LOGIN_RESP | jq -r .auth.access_token)

if [ "$TOKEN" == "null" ]; then
    echo -e "${RED}Failed${NC}"
    echo "Response: $LOGIN_RESP"
    exit 1
fi
echo -e "${GREEN}Success${NC}"

# 2. Add Broker Account
echo -n "Adding OANDA Broker Account... "
# Mock credentials - using format expected by BrokerFactory
# Note: For OANDA, we need api_key and account_id
CREDS='{"api_key": "mock-api-key-123", "account_id": "mock-acc-001", "environment": "practice"}'

ADD_RESP=$(curl -v -s -X POST "$API_URL/accounts/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"broker_name\": \"OANDA\",
    \"account_name\": \"My Test OANDA\",
    \"account_number\": \"001-001-TEST\",
    \"is_live\": false,
    \"credentials\": $CREDS
  }")

ACCOUNT_ID=$(echo $ADD_RESP | jq -r .data.id)

if [ "$ACCOUNT_ID" == "null" ] || [ -z "$ACCOUNT_ID" ]; then
    echo -e "${RED}Failed${NC}"
    echo "Response: $ADD_RESP"
    exit 1
fi
echo -e "${GREEN}Success (ID: $ACCOUNT_ID)${NC}"

# 3. List Accounts
echo -n "Listing Accounts... "
LIST_RESP=$(curl -s -X GET "$API_URL/accounts/" \
  -H "Authorization: Bearer $TOKEN")

COUNT=$(echo $LIST_RESP | jq '.data | length')
if [ "$COUNT" -ge 1 ]; then
    echo -e "${GREEN}Success (Found $COUNT accounts)${NC}"
else
    echo -e "${RED}Failed (No accounts found)${NC}"
    exit 1
fi

# 4. Trigger Trade Sync (This exercises the execution client + factory)
# We expect this to potentially fail internally in execution service due to bad creds,
# but the API call should return successfully (handling the error gracefully)
echo -n "Triggering Trade Sync... "
SYNC_RESP=$(curl -s -X GET "$API_URL/execution/trades?status=OPEN" \
  -H "Authorization: Bearer $TOKEN")

STATUS=$(echo $SYNC_RESP | jq -r .status)

if [ "$STATUS" == "success" ]; then
    echo -e "${GREEN}Success (Sync triggered)${NC}"
else
    echo -e "${RED}Failed${NC}"
    echo "Response: $SYNC_RESP"
fi

# 5. Clean up (Delete Account)
echo -n "Deleting Test Account... "
DEL_RESP=$(curl -s -X DELETE "$API_URL/accounts/$ACCOUNT_ID" \
  -H "Authorization: Bearer $TOKEN")

DEL_STATUS=$(echo $DEL_RESP | jq -r .status)
if [ "$DEL_STATUS" == "success" ]; then
    echo -e "${GREEN}Success${NC}"
else
    echo -e "${RED}Failed${NC}"
fi

echo -e "${GREEN}Test Complete${NC}"
