#!/bin/bash
# Settings API Manual Testing Script
# This script tests all new endpoints: Fund, Settings, Auth updates

echo "🧪 MTF Trading System - Settings API Testing"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Login and get token
echo -e "${BLUE}1. Login (POST /api/v1/auth/token)${NC}"
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=trader1&password=password123" \
  | jq -r '.auth.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo -e "${YELLOW}⚠️  Login failed. Token not received.${NC}"
  echo "Make sure backend is running and user 'trader1' exists"
  exit 1
fi

echo -e "${GREEN}✅ Login successful${NC}"
echo "Token: ${TOKEN:0:20}..."
echo ""

# 2. Get current profile
echo -e "${BLUE}2. Get Profile (GET /api/v1/auth/profile)${NC}"
curl -s http://localhost:8000/api/v1/auth/profile \
  -H "Authorization: Bearer $TOKEN" \
  | jq
echo ""

# 3. Get user funds
echo -e "${BLUE}3. Get User Funds (GET /api/v1/funds)${NC}"
curl -s http://localhost:8000/api/v1/funds \
  -H "Authorization: Bearer $TOKEN" \
  | jq
echo ""

# 4. Get user preferences (should auto-create if none exist)
echo -e "${BLUE}4. Get User Preferences (GET /api/v1/settings/preferences)${NC}"
curl -s http://localhost:8000/api/v1/settings/preferences \
  -H "Authorization: Bearer $TOKEN" \
  | jq
echo ""

# 5. Update basic risk parameters
echo -e "${BLUE}5. Update Risk Parameters (PUT /api/v1/settings/preferences)${NC}"
curl -s -X PUT http://localhost:8000/api/v1/settings/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_risk_per_trade": 5.0,
    "default_lot_size": 0.02,
    "preferred_timeframes": ["4H", "1H"]
  }' \
  | jq
echo ""

# 6. Try to change default symbol with MTF_SMC_BASIC (should fail)
echo -e "${BLUE}6. Test XAU/USD Validation (PUT /api/v1/settings/preferences - should FAIL)${NC}"
curl -s -X PUT http://localhost:8000/api/v1/settings/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "default_symbol": "EUR/USD"
  }' \
  | jq
echo ""

# 7. Change strategy to LONG_SHORT_EQUITY
echo -e "${BLUE}7. Update Strategy Type (PUT /api/v1/settings/preferences)${NC}"
curl -s -X PUT http://localhost:8000/api/v1/settings/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_type": "LONG_SHORT_EQUITY",
    "asset_classes": ["EQUITY", "FX"],
    "gross_exposure_limit": 200.0,
    "net_exposure_limit": 20.0,
    "max_portfolio_beta": 0.4
  }' \
  | jq
echo ""

# 8. Now change symbol (should succeed with advanced strategy)
echo -e "${BLUE}8. Update Symbol with Advanced Strategy (PUT /api/v1/settings/preferences)${NC}"
curl -s -X PUT http://localhost:8000/api/v1/settings/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "default_symbol": "SPX",
    "supported_symbols": ["SPX", "QQQ", "EUR/USD", "GC"]
  }' \
  | jq
echo ""

# 9. Update trading sessions
echo -e "${BLUE}9. Update Session Preferences (PUT /api/v1/settings/preferences)${NC}"
curl -s -X PUT http://localhost:8000/api/v1/settings/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_preferences": ["LONDON", "NY"]
  }' \
  | jq
echo ""

# 10. Get updated preferences
echo -e "${BLUE}10. Get Updated Preferences (GET /api/v1/settings/preferences)${NC}"
curl -s http://localhost:8000/api/v1/settings/preferences \
  -H "Authorization: Bearer $TOKEN" \
  | jq
echo ""

# 11. Update profile
echo -e "${BLUE}11. Update Profile (PUT /api/v1/auth/profile)${NC}"
curl -s -X PUT http://localhost:8000/api/v1/auth/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader1_updated@example.com"
  }' \
  | jq
echo ""

# 12. Change password
echo -e "${BLUE}12. Change Password (PUT /api/v1/auth/password)${NC}"
curl -s -X PUT http://localhost:8000/api/v1/auth/password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "password123",
    "new_password": "newpassword456"
  }' \
  | jq
echo ""

# 13. Test new password
echo -e "${BLUE}13. Test New Password (POST /api/v1/auth/token)${NC}"
NEW_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=trader1&password=newpassword456" \
  | jq -r '.auth.access_token')

if [ "$NEW_TOKEN" == "null" ] || [ -z "$NEW_TOKEN" ]; then
  echo -e "${YELLOW}⚠️  New password login failed${NC}"
else
  echo -e "${GREEN}✅ New password works!${NC}"
  echo "New Token: ${NEW_TOKEN:0:20}..."
fi
echo ""

# 14. Reset password back
echo -e "${BLUE}14. Reset Password (PUT /api/v1/auth/password)${NC}"
curl -s -X PUT http://localhost:8000/api/v1/auth/password \
  -H "Authorization: Bearer $NEW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "newpassword456",
    "new_password": "password123"
  }' \
  | jq
echo ""

echo -e "${GREEN}=============================================="
echo "✅ All tests completed!"
echo "==============================================${NC}"
