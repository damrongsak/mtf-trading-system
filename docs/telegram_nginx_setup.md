# Telegram Webhook with Nginx - Production Setup Guide

## Overview
This guide shows how to configure Nginx as a reverse proxy for the Telegram webhook, eliminating the need for ngrok in production or local development.

## Architecture

```
Telegram Bot API
    ↓ (HTTPS)
Your Domain (e.g., mtf.yourdomain.com)
    ↓
Nginx (Port 443/80)
    ↓
API Gateway Container (Port 8000)
    ↓
/api/v1/telegram/webhook endpoint
```

## Option 1: Production Setup (with SSL)

### 1. Nginx Configuration

Create or update `/home/dan/workspace/mtf-trading-system/infra/nginx/mtf-telegram.conf`:

```nginx
# Upstream for API Gateway
upstream api_gateway {
    server api-gateway:8000;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name mtf.yourdomain.com;
    
    # Allow Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name mtf.yourdomain.com;
    
    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/mtf.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mtf.yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Telegram webhook endpoint
    location /api/v1/telegram/webhook {
        proxy_pass http://api_gateway;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Rate limiting (optional but recommended)
        limit_req zone=telegram_webhook burst=10 nodelay;
    }
    
    # Other API endpoints
    location /api/ {
        proxy_pass http://api_gateway;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Health check
    location /health {
        proxy_pass http://api_gateway;
        access_log off;
    }
}

# Rate limiting zone for Telegram webhook
limit_req_zone $binary_remote_addr zone=telegram_webhook:10m rate=30r/m;
```

### 2. Docker Compose Integration

Update `docker-compose.yml` to include Nginx:

```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infra/nginx:/etc/nginx/conf.d
      - ./infra/certbot/conf:/etc/letsencrypt
      - ./infra/certbot/www:/var/www/certbot
    depends_on:
      - api-gateway
    networks:
      - mtf-network
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    container_name: certbot
    volumes:
      - ./infra/certbot/conf:/etc/letsencrypt
      - ./infra/certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

### 3. SSL Certificate Setup (Let's Encrypt)

```bash
# Initial certificate request
docker compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d mtf.yourdomain.com

# Restart Nginx to load certificates
docker compose restart nginx
```

### 4. Register Webhook with Telegram

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_WEBHOOK_URL="https://mtf.yourdomain.com/api/v1/telegram/webhook"
export TELEGRAM_WEBHOOK_SECRET="mtf_olympus_webhook_secret"

python scripts/setup_telegram_webhook.py setup
```

---

## Option 2: Local Development Setup (without SSL)

For local development, you can use Nginx without SSL by exposing it on a custom port.

### 1. Nginx Configuration (Local)

Create `/home/dan/workspace/mtf-trading-system/infra/nginx/local-telegram.conf`:

```nginx
upstream api_gateway {
    server api-gateway:8000;
}

server {
    listen 8080;
    server_name localhost;
    
    location /api/v1/telegram/webhook {
        proxy_pass http://api_gateway;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /api/ {
        proxy_pass http://api_gateway;
    }
    
    location /health {
        proxy_pass http://api_gateway;
    }
}
```

### 2. Use ngrok to expose Nginx

```bash
# Start Nginx on port 8080
docker compose up nginx

# Expose via ngrok
ngrok http 8080
```

This gives you the benefits of Nginx (rate limiting, logging, etc.) while still using ngrok for HTTPS tunneling during development.

---

## Option 3: Cloudflare Tunnel (Alternative to ngrok)

If you want to avoid ngrok entirely, use Cloudflare Tunnel:

### 1. Install cloudflared

```bash
# Download cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### 2. Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

### 3. Create and Configure Tunnel

```bash
# Create tunnel
cloudflared tunnel create mtf-telegram

# Configure tunnel
cat > ~/.cloudflared/config.yml <<EOF
tunnel: mtf-telegram
credentials-file: /home/user/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: mtf.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Run tunnel
cloudflared tunnel run mtf-telegram
```

### 4. DNS Configuration

Add a CNAME record in Cloudflare:
- Type: `CNAME`
- Name: `mtf` (or your subdomain)
- Target: `<TUNNEL-ID>.cfargotunnel.com`

---

## Testing the Setup

### 1. Verify Nginx is routing correctly

```bash
# Test health endpoint
curl http://localhost:8080/health

# Test via your domain (production)
curl https://mtf.yourdomain.com/health
```

### 2. Register webhook

```bash
python scripts/setup_telegram_webhook.py setup
```

### 3. Check webhook status

```bash
python scripts/setup_telegram_webhook.py info
```

### 4. Monitor Nginx logs

```bash
# Access logs
docker compose logs nginx -f

# Error logs
docker compose exec nginx tail -f /var/log/nginx/error.log
```

---

## Security Best Practices

1. **Rate Limiting**: Already configured in the Nginx example above
2. **IP Whitelisting** (optional): Restrict to Telegram's IP ranges
   ```nginx
   # Add to location /api/v1/telegram/webhook
   allow 149.154.160.0/20;
   allow 91.108.4.0/22;
   deny all;
   ```
3. **Webhook Secret**: Always validate the `X-Telegram-Bot-Api-Secret-Token` header
4. **HTTPS Only**: Telegram requires HTTPS for webhooks in production
5. **Firewall**: Only expose ports 80 and 443 externally

---

## Troubleshooting

### Nginx not starting
```bash
# Check configuration syntax
docker compose exec nginx nginx -t

# View logs
docker compose logs nginx
```

### SSL certificate issues
```bash
# Renew manually
docker compose run --rm certbot renew

# Check certificate expiry
docker compose exec nginx openssl x509 -in /etc/letsencrypt/live/mtf.yourdomain.com/fullchain.pem -noout -dates
```

### Webhook not receiving messages
```bash
# Check Nginx access logs
docker compose logs nginx | grep telegram

# Verify API Gateway is reachable
docker compose exec nginx curl http://api-gateway:8000/health
```

---

## Recommended Approach

**For Production**: Use **Option 1** (Nginx + Let's Encrypt)
**For Local Dev**: Use **Option 2** (Nginx + ngrok) or **Option 3** (Cloudflare Tunnel)

The Nginx approach gives you:
- ✅ Better performance
- ✅ Rate limiting
- ✅ SSL termination
- ✅ Request logging
- ✅ Production-ready architecture
