# Quick Start: Telegram Webhook with Nginx

## For Local Development (Simplest)

### 1. Your Nginx is already configured! ✅
The webhook endpoint is now available at: `http://localhost/api/v1/telegram/webhook`

### 2. Expose via ngrok
```bash
# Install ngrok (if not already installed)
# Download from: https://ngrok.com/download

# Expose your Nginx (port 80)
ngrok http 80
```

### 3. Copy the HTTPS URL from ngrok
Example: `https://abc123.ngrok-free.app`

### 4. Register webhook with Telegram
```bash
export TELEGRAM_BOT_TOKEN="8367617972:AAE5srGYV2W0iN2knq5Vw5ckyimUJt1XA44"
export TELEGRAM_WEBHOOK_URL="https://abc123.ngrok-free.app/api/v1/telegram/webhook"
export TELEGRAM_WEBHOOK_SECRET="mtf_olympus_webhook_secret"

python scripts/setup_telegram_webhook.py setup
```

### 5. Link your Telegram account
```bash
# Get your chat_id by messaging your bot, then:
curl -X POST "http://localhost/api/v1/telegram/link" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 916700879}'
```

### 6. Test it!
Send a message to your Telegram bot:
```
What's my account balance?
```

---

## For Production (with your own domain)

### Prerequisites
- A domain name (e.g., `mtf.yourdomain.com`)
- DNS configured to point to your server
- Ports 80 and 443 open

### 1. Install Certbot for SSL
```bash
# Add certbot service to docker-compose.yml (already in docs/telegram_nginx_setup.md)
docker compose up -d certbot
```

### 2. Get SSL certificate
```bash
docker compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  -d mtf.yourdomain.com
```

### 3. Use the production Nginx config
```bash
# Copy the production config
cp infra/nginx/mtf-telegram.conf infra/nginx/default.conf

# Update with your domain name
sed -i 's/mtf.yourdomain.com/YOUR_ACTUAL_DOMAIN/g' infra/nginx/default.conf

# Restart Nginx
docker compose restart nginx
```

### 4. Register webhook
```bash
export TELEGRAM_WEBHOOK_URL="https://YOUR_ACTUAL_DOMAIN/api/v1/telegram/webhook"
python scripts/setup_telegram_webhook.py setup
```

---

## Verification

### Check Nginx is working
```bash
curl http://localhost/health
# Should return: {"status":"ok"}
```

### Check webhook status
```bash
python scripts/setup_telegram_webhook.py info
```

### Monitor logs
```bash
# Nginx logs
docker compose logs nginx -f

# API Gateway logs
docker compose logs api-gateway -f
```

---

## Benefits of Using Nginx

✅ **Rate Limiting**: Protects against spam (30 req/min configured)  
✅ **Better Logging**: All requests logged by Nginx  
✅ **SSL Termination**: Handles HTTPS for you  
✅ **Production Ready**: Same setup for dev and prod  
✅ **No ngrok in Production**: Use your own domain  

---

## Troubleshooting

**Nginx config error?**
```bash
docker compose exec nginx nginx -t
```

**Webhook not receiving messages?**
```bash
# Check if endpoint is reachable
curl http://localhost/api/v1/telegram/webhook

# Check Nginx logs
docker compose logs nginx | grep telegram
```

**Rate limit too strict?**
Edit `infra/nginx/default.conf` and change:
```nginx
limit_req_zone $binary_remote_addr zone=telegram_webhook:10m rate=30r/m;
```
to a higher rate (e.g., `rate=60r/m`)

Then restart: `docker compose restart nginx`
