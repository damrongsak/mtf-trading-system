import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the service directory to path to import agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-analyst")))

from app.routers.agents import send_telegram_message

async def test_formatting():
    load_dotenv()
    chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "916700879"))
    
    print(f"🚀 Testing Telegram HTML Formatting for chat_id: {chat_id}")
    
    test_cases = [
        {
            "name": "Basic Bold/Italic",
            "text": "Hello! This is **bold** and this is *italic*."
        },
        {
            "name": "Special Characters (Unescaped in Markdown)",
            "text": "Price dropped by -2.5%! (Check [XAUUSD] alert). 1+1=2. #Analysis"
        },
        {
            "name": "Inline Code",
            "text": "The variable is `price_action`."
        },
        {
            "name": "Code Block",
            "text": "```python\nif price > 2000:\n    print('SELL')\n```"
        },
        {
            "name": "Complex Mixed",
            "text": "MTF Analysis for **XAU/USD**:\n- Trend: *Bearish*\n- RS: `RSI < 30`!\n- Action: **Wait** for 15m confirmation."
        }
    ]
    
    for case in test_cases:
        print(f"Testing: {case['name']}...")
        success = await send_telegram_message(
            chat_id=chat_id,
            text=case['text'],
            parse_mode="HTML"
        )
        if success:
            print(f"✅ {case['name']} sent successfully.")
        else:
            print(f"❌ {case['name']} failed.")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_formatting())
