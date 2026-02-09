# End-to-End Telegram Testing Guide

## Pre-Test Checklist

Run these commands to verify everything is ready:

```bash
# 1. Check services
docker compose ps | grep -E "(nginx|api-gateway|ai-analyst)"

# 2. Check webhook status
curl -s "https://api.telegram.org/bot8367617972:AAE5srGYV2W0iN2knq5Vw5ckyimUJt1XA44/getWebhookInfo" | python3 -m json.tool

# 3. Verify account linking
curl -s -X POST "http://localhost/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=trader1&password=password123" | python3 -c "import sys, json; print(json.load(sys.stdin)['auth']['access_token'])"

# Save the token, then check status:
curl -s -X GET "http://localhost/api/v1/telegram/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Test Scenarios

### Test 1: Simple Query
**Send to @sodaTalk_bot:**
```
Hello! Can you hear me?
```

**Expected:**
- ✅ Webhook receives message
- ✅ AI Analyst processes query
- ✅ Response sent back to Telegram
- ✅ You receive a friendly greeting

**Monitor:**
```bash
# Watch webhook logs
docker compose logs nginx -f | grep telegram

# Watch AI processing
docker compose logs ai-analyst -f
```

### Test 2: Tool Execution (SMC Analysis)
**Send to @sodaTalk_bot:**
```
Analyze XAUUSD on H1 timeframe
```

**Expected:**
- ✅ AI calls SMCAnalystTool
- ✅ Fetches market data
- ✅ Returns structured analysis with:
  - Market structure (bullish/bearish)
  - Key levels (support/resistance)
  - Fair Value Gaps
  - Order blocks
- ✅ Response formatted in Markdown

### Test 3: Multi-Tool Execution
**Send to @sodaTalk_bot:**
```
Analyze XAUUSD on M5 and plan a trade
```

**Expected:**
- ✅ AI calls SMCAnalystTool for M5 analysis
- ✅ AI calls TradePlannerTool with analysis results
- ✅ Returns comprehensive trade plan with:
  - Entry price
  - Stop loss
  - Take profit
  - Risk-reward ratio
  - Position size

### Test 4: Account Information
**Send to @sodaTalk_bot:**
```
What's my account balance?
```

**Expected:**
- ✅ AI retrieves user account info
- ✅ Returns balance and account details

### Test 5: Error Handling
**Send to @sodaTalk_bot:**
```
Analyze INVALID_SYMBOL on H1
```

**Expected:**
- ✅ AI handles error gracefully
- ✅ Returns helpful error message
- ✅ No crash or 500 error

## Monitoring Commands

### Real-Time Log Monitoring

**Terminal 1 - Nginx (Webhook):**
```bash
docker compose logs nginx -f | grep -E "(telegram|webhook)"
```

**Terminal 2 - API Gateway:**
```bash
docker compose logs api-gateway -f | grep -E "(telegram|webhook)"
```

**Terminal 3 - AI Analyst:**
```bash
docker compose logs ai-analyst -f
```

### Check Recent Activity

```bash
# Last 50 lines from each service
docker compose logs nginx --tail 50 | grep telegram
docker compose logs api-gateway --tail 50 | grep telegram
docker compose logs ai-analyst --tail 50
```

### Verify Database Updates

```bash
# Check if messages are being logged (if implemented)
docker exec mtf-postgres psql -U trader -d mtf_db -c "SELECT * FROM telegram_chat_mappings WHERE chat_id = 916700879;"
```

## Success Criteria

✅ **Webhook Delivery**: Message appears in nginx logs  
✅ **Signature Validation**: No 403 errors in api-gateway  
✅ **User Lookup**: chat_id correctly mapped to trader1  
✅ **AI Processing**: AI Analyst receives and processes message  
✅ **Tool Execution**: Tools are called when needed  
✅ **Response Delivery**: Response sent back to Telegram  
✅ **User Receives**: Message appears in your Telegram chat  

## Troubleshooting

### No Response from Bot

1. **Check webhook:**
   ```bash
   curl -s "https://api.telegram.org/bot8367617972:AAE5srGYV2W0iN2knq5Vw5ckyimUJt1XA44/getWebhookInfo"
   ```

2. **Check nginx logs:**
   ```bash
   docker compose logs nginx --tail 100 | grep telegram
   ```

3. **Check API Gateway:**
   ```bash
   docker compose logs api-gateway --tail 100 | grep telegram
   ```

### Bot Responds with Error

1. **Check AI Analyst logs:**
   ```bash
   docker compose logs ai-analyst --tail 100
   ```

2. **Verify bot token:**
   ```bash
   docker exec ai-analyst sh -c 'echo $TELEGRAM_BOT_TOKEN'
   ```

### Webhook Not Receiving Messages

1. **Verify ngrok is running:**
   ```bash
   curl https://38fa-223-24-159-28.ngrok-free.app/health
   ```

2. **Re-register webhook:**
   ```bash
   ./scripts/configure_telegram_webhook.sh setup
   ```

## Performance Metrics

Track these during testing:

- **Response Time**: Time from message sent to response received
- **Tool Execution**: Number of tools called per query
- **Error Rate**: Percentage of failed requests
- **Webhook Latency**: Time for webhook to reach API Gateway

## Next Steps After Testing

1. Document any issues found
2. Fix bugs if discovered
3. Optimize response times if needed
4. Add more test scenarios
5. Consider load testing with multiple users
