# Telegram Webhook - Ready to Test! ✅

## Webhook Status
- **URL**: `https://38fa-223-24-159-28.ngrok-free.app/api/v1/telegram/webhook`
- **Status**: ✅ Active
- **Pending Updates**: 0
- **Secret Token**: Configured

## Next Steps

### 1. Link Your Telegram Account

You need to link your Telegram `chat_id` (916700879) to your MTF user account.

**Option A: Via API (requires JWT token)**
```bash
curl -X POST "http://localhost/api/v1/telegram/link" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 916700879}'
```

**Option B: Get JWT token first**
```bash
# Login to get JWT token
curl -X POST "http://localhost/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# Copy the "access_token" from response
# Then use it in Option A above
```

### 2. Test the Integration

Once linked, send any message to your Telegram bot:
```
What's my account balance?
```

Or try:
```
Analyze XAUUSD on H1 timeframe
```

Or:
```
Plan a trade for XAUUSD on M5
```

### 3. Monitor Logs

**Watch for incoming webhooks:**
```bash
docker compose logs nginx -f | grep telegram
```

**Watch AI Analyst processing:**
```bash
docker compose logs ai-analyst -f
```

**Watch API Gateway:**
```bash
docker compose logs api-gateway -f
```

## Troubleshooting

### "Account Not Linked" message in Telegram
- You haven't linked your chat_id yet. Complete Step 1 above.

### No response from bot
- Check if webhook is receiving requests: `docker compose logs nginx | grep webhook`
- Verify API Gateway is running: `curl http://localhost/health`
- Check AI Analyst logs: `docker compose logs ai-analyst --tail 50`

### Get current webhook info
```bash
curl -s "https://api.telegram.org/bot8367617972:AAE5srGYV2W0iN2knq5Vw5ckyimUJt1XA44/getWebhookInfo" | python3 -m json.tool
```

## Expected Flow

1. **You send**: "What's my account balance?"
2. **Telegram** → sends webhook to ngrok URL
3. **Nginx** → routes to API Gateway `/telegram/webhook`
4. **API Gateway** → validates signature, looks up user_id from chat_id
5. **API Gateway** → forwards to AI Analyst
6. **AI Analyst** → processes query, generates response
7. **AI Analyst** → sends response back to Telegram
8. **You receive**: AI's response in Telegram

---

**Status**: 🟢 Ready for testing!
**Next**: Link your account and start chatting!
