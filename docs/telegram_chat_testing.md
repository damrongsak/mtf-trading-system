# Telegram Chat Integration - Testing Guide

## Prerequisites
- Telegram bot token configured in environment variables
- Services running: `api-gateway`, `ai-analyst`, `strategy-core`
- Database migration applied (creates `telegram_chat_mappings` table)

## Phase 4: Testing & Deployment

### Step 1: Setup Webhook (Local Development with ngrok)

1. **Install and start ngrok:**
   ```bash
   ngrok http 8000
   ```

2. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

3. **Set environment variables:**
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export TELEGRAM_WEBHOOK_URL="https://abc123.ngrok.io/api/v1/telegram/webhook"
   export TELEGRAM_WEBHOOK_SECRET="mtf_olympus_webhook_secret"
   ```

4. **Register webhook:**
   ```bash
   python scripts/setup_telegram_webhook.py setup
   ```

5. **Verify webhook:**
   ```bash
   python scripts/setup_telegram_webhook.py info
   ```

### Step 2: Link Telegram Account

**Option A: Via API (Recommended for Testing)**
```bash
# Get your chat_id by sending /start to your bot, then check Telegram API
curl -X POST "http://localhost:8000/api/v1/telegram/link" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": YOUR_CHAT_ID}'
```

**Option B: Via Web UI (Future)**
- Navigate to Settings → Integrations → Link Telegram
- Send `/start` to your bot
- Click "Link Account"

### Step 3: Test End-to-End Flow

1. **Send a message to your Telegram bot:**
   ```
   What's my account balance?
   ```

2. **Expected flow:**
   - Telegram → Webhook → API Gateway → AI Analyst
   - AI Analyst processes query
   - AI Analyst → Telegram (response sent back)

3. **Verify response in Telegram**

### Step 4: Test Complex Queries

**Test Case 1: Market Analysis**
```
Analyze XAUUSD on H1 timeframe
```

**Test Case 2: Trade Planning**
```
Plan a trade for XAUUSD on M5
```

**Test Case 3: Multi-Step Query**
```
What's the current market structure for XAUUSD and should I enter a trade?
```

## Troubleshooting

### Webhook Not Receiving Messages
- Check ngrok is running: `curl https://your-ngrok-url.ngrok.io/health`
- Verify webhook info: `python scripts/setup_telegram_webhook.py info`
- Check API Gateway logs: `docker compose logs api-gateway --tail 100`

### Account Not Linked Error
- Verify chat_id is correct
- Check database: `SELECT * FROM telegram_chat_mappings;`
- Ensure user is authenticated when calling `/telegram/link`

### AI Not Responding
- Check AI Analyst logs: `docker compose logs ai-analyst --tail 100`
- Verify `TELEGRAM_BOT_TOKEN` is set in environment
- Test AI Analyst directly: `curl -X POST http://localhost:8001/api/v1/ai/chat/sessions/message`

## Production Deployment

1. **Use a proper domain** instead of ngrok
2. **Set webhook URL** to your production domain
3. **Enable HTTPS** (required by Telegram)
4. **Add rate limiting** to webhook endpoint
5. **Monitor webhook health** via `/telegram/status`

## Security Checklist
- ✅ Webhook signature validation enabled
- ✅ Rate limiting configured
- ✅ User authentication required for linking
- ✅ Chat_id uniqueness enforced in database
- ✅ Environment variables secured
