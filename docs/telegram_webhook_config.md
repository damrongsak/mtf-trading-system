# Telegram Webhook Configuration

## Configuration in .env

All Telegram settings are now centralized in your `.env` file:

```bash
# Telegram
TELEGRAM_CHAT_ID=916700879
TELEGRAM_BOT_TOKEN=8367617972:AAE5srGYV2W0iN2knq5Vw5ckyimUJt1XA44
TELEGRAM_WEBHOOK_URL=https://38fa-223-24-159-28.ngrok-free.app/api/v1/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=mtf_olympus_webhook_secret
```

## Managing Webhook

### Setup Webhook (from .env)
```bash
python3 scripts/configure_telegram_webhook.py setup
```

This reads `TELEGRAM_WEBHOOK_URL` from `.env` and registers it with Telegram.

### Check Webhook Status
```bash
python3 scripts/configure_telegram_webhook.py info
```

### Delete Webhook
```bash
python3 scripts/configure_telegram_webhook.py delete
```

## When ngrok URL Changes

1. **Update `.env` file**:
   ```bash
   # Change this line to your new ngrok URL
   TELEGRAM_WEBHOOK_URL=https://NEW_NGROK_URL/api/v1/telegram/webhook
   ```

2. **Re-register webhook**:
   ```bash
   python3 scripts/configure_telegram_webhook.py setup
   ```

That's it! No need to pass environment variables manually.

## Architecture Benefits

✅ **Centralized Configuration**: All settings in one place (`.env`)  
✅ **Version Control**: `.env.example` can be committed for reference  
✅ **Docker Integration**: Automatically loaded by `docker-compose.yml`  
✅ **Consistency**: Same pattern as other service URLs in the project  
✅ **Easy Updates**: Just edit `.env` and run setup script  

## Production Deployment

For production, replace the ngrok URL with your actual domain:

```bash
TELEGRAM_WEBHOOK_URL=https://mtf.yourdomain.com/api/v1/telegram/webhook
```

Then run:
```bash
python3 scripts/configure_telegram_webhook.py setup
```
