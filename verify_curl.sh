#!/bin/bash

# 1. Login
echo "Logging in..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=trader1&password=password123" \
  | jq -r '.auth.access_token')

if [ "$TOKEN" == "null" ]; then
    echo "Login failed. Trying to register..."
    # Register if login fails
    curl -s -X POST http://localhost:8000/api/v1/auth/register \
      -H "Content-Type: application/json" \
      -d '{"username": "trader1", "email": "trader1@example.com", "password": "password123"}' > /dev/null
    
    TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=trader1&password=password123" \
      | jq -r '.auth.access_token')
fi

echo "Token: $TOKEN"

# 2. Get Fund
echo -e "\nGetting Funds..."
FUND_ID=$(curl -s -X GET http://localhost:8000/api/v1/funds \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.data[0].id')

if [ "$FUND_ID" == "null" ]; then
    echo "No fund found. Creating one..."
    FUND_ID=$(curl -s -X POST http://localhost:8000/api/v1/funds \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"name": "My Growth Fund", "description": "Test Fund"}' \
      | jq -r '.data.id')
fi

echo "Fund ID: $FUND_ID"

# 3. Create Transaction
echo -e "\nCreating Deposit Transaction..."
curl -s -X POST http://localhost:8000/api/v1/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fund_id": "'$FUND_ID'",
    "transaction_date": "2025-12-05T10:00:00Z",
    "type": "DEPOSIT",
    "amount": 5000.00,
    "currency": "USD",
    "status": "COMPLETED",
    "description": "Initial Funding"
  }' | jq

# 4. List Transactions
echo -e "\nListing Transactions..."
curl -s -X GET "http://localhost:8000/api/v1/transactions?fund_id=$FUND_ID" \
  -H "Authorization: Bearer $TOKEN" | jq

# 5. Get Balance
echo -e "\nGetting Balance..."
curl -s -X GET "http://localhost:8000/api/v1/transactions/balance?fund_id=$FUND_ID" \
  -H "Authorization: Bearer $TOKEN" | jq

# 6. Import Excel
echo -e "\nImporting Excel..."
curl -s -X POST http://localhost:8000/api/v1/transactions/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "fund_id=$FUND_ID" \
  -F "file=@/home/dan/workspace/mtf-trading-system/example/transaction_history_statement_72147_20000101_20251205.xlsx" | jq

# 7. Get Balance Again
echo -e "\nGetting Balance After Import..."
curl -s -X GET "http://localhost:8000/api/v1/transactions/balance?fund_id=$FUND_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
