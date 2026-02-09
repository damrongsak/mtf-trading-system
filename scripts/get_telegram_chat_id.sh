#!/bin/bash
# Get Telegram Chat ID from recent updates

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-8367617972:AAE5srGYV2W0iN2knq5Vw5ckyimUJt1XA44}"

echo "📱 Fetching recent Telegram updates..."
echo ""
echo "💡 TIP: Send a message to your bot first, then run this script"
echo ""

response=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getUpdates")

# Extract chat IDs using python
echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('ok') and data.get('result'):
    updates = data['result']
    if not updates:
        print('❌ No recent messages found.')
        print('   Send a message to your bot first!')
    else:
        print('✅ Recent chat IDs:')
        print('')
        seen = set()
        for update in reversed(updates[-5:]):  # Last 5 updates
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                username = update['message']['chat'].get('username', 'N/A')
                first_name = update['message']['chat'].get('first_name', 'N/A')
                text = update['message'].get('text', '')[:50]
                
                if chat_id not in seen:
                    seen.add(chat_id)
                    print(f'   Chat ID: {chat_id}')
                    print(f'   Name: {first_name}')
                    print(f'   Username: @{username}')
                    print(f'   Last message: \"{text}\"')
                    print('')
else:
    print('❌ Error fetching updates')
    print(data.get('description', 'Unknown error'))
"
