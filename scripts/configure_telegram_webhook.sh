#!/bin/bash
# Telegram Webhook Configuration Script
# Reads configuration from .env file

set -e

# Load .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found"
    exit 1
fi

# Check required variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN not found in .env"
    exit 1
fi

# Command handling
case "${1:-}" in
    setup)
        if [ -z "$TELEGRAM_WEBHOOK_URL" ]; then
            echo "❌ TELEGRAM_WEBHOOK_URL not found in .env"
            echo "Please add TELEGRAM_WEBHOOK_URL to your .env file"
            exit 1
        fi
        
        echo "📡 Setting webhook to: $TELEGRAM_WEBHOOK_URL"
        
        response=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
            -H "Content-Type: application/json" \
            -d "{
                \"url\": \"$TELEGRAM_WEBHOOK_URL\",
                \"secret_token\": \"${TELEGRAM_WEBHOOK_SECRET:-mtf_olympus_webhook_secret}\",
                \"allowed_updates\": [\"message\"]
            }")
        
        if echo "$response" | grep -q '"ok":true'; then
            echo "✅ Webhook configured successfully!"
            echo "   URL: $TELEGRAM_WEBHOOK_URL"
            echo "   Secret: ${TELEGRAM_WEBHOOK_SECRET:-mtf_olympus_webhook_secret}"
        else
            echo "❌ Failed to set webhook:"
            echo "$response" | python3 -m json.tool
            exit 1
        fi
        ;;
        
    info)
        echo ""
        echo "📊 Current Webhook Configuration:"
        curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | python3 -m json.tool
        ;;
        
    delete)
        response=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook")
        
        if echo "$response" | grep -q '"ok":true'; then
            echo "✅ Webhook deleted successfully!"
        else
            echo "❌ Failed to delete webhook:"
            echo "$response" | python3 -m json.tool
        fi
        ;;
        
    *)
        echo "Usage: $0 [setup|info|delete]"
        echo ""
        echo "Commands:"
        echo "  setup  - Configure webhook from .env settings"
        echo "  info   - Show current webhook configuration"
        echo "  delete - Remove webhook configuration"
        exit 1
        ;;
esac
