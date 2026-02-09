# Telegram Configuration - Quick Reference

## All Settings in .env

```bash
# Telegram Configuration
TELEGRAM_CHAT_ID=916700879                                                    # Your Telegram chat ID
TELEGRAM_BOT_TOKEN=8367617972:AAE5srGYV2W0iN2knq5Vw5ckyimUJt1XA44            # Bot token from @BotFather
TELEGRAM_WEBHOOK_URL=https://38fa-223-24-159-28.ngrok-free.app/api/v1/telegram/webhook  # Webhook endpoint
TELEGRAM_WEBHOOK_SECRET=mtf_olympus_webhook_secret                           # Secret for signature validation
```

## Quick Commands

### Configure Webhook
```bash
python3 scripts/configure_telegram_webhook.py setup
```

### Check Status
```bash
python3 scripts/configure_telegram_webhook.py info
```

### Delete Webhook
```bash
python3 scripts/configure_telegram_webhook.py delete
```

## When ngrok Restarts

1. Get new ngrok URL:
   ```bash
   ngrok http 80
   # Copy the HTTPS URL
   ```

2. Update `.env`:
   ```bash
   TELEGRAM_WEBHOOK_URL=https://NEW_URL.ngrok-free.app/api/v1/telegram/webhook
   ```

3. Re-register:
   ```bash
   python3 scripts/configure_telegram_webhook.py setup
   ```

## Architecture Alignment

This follows the same pattern as other services in the project:

```bash
# Service URLs (all in .env)
STRATEGY_CORE_URL=http://strategy-core:8000
EXECUTION_SERVICE_URL=http://execution:8000
AI_ANALYST_URL=http://ai-analyst:8000
TELEGRAM_WEBHOOK_URL=https://...  # ← Same pattern!
```

✅ Centralized configuration  
✅ Environment-based  
✅ Docker-compose compatible  
✅ Easy to update
