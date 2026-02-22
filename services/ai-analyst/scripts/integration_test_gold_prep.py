import asyncio
import httpx
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integration-test")

async def run_integration_test():
    """
    Simulates a user requesting a weekly gold trading preparation.
    Triggers the Strategy Advisor Agent and verifies Telegram integration.
    """
    url = "http://localhost:8000/api/v1/ai/chat/sessions/message"
    
    # Formulate the complex preparation query
    query = """
    Tomorrow is Monday 2026-02-23. Help me prepare for the gold trading week ahead.
    Please perform the following analysis:
    1. Macro structural bias for XAUUSD on 4H/Daily.
    2. Key POIs (Order Blocks/FVGs) for the week.
    3. ML price forecast for the next 5 steps from Olympus Predictor.
    4. Market state and any significant news/sentiment drivers.
    
    Summarize these into a 'Weekly Preparation Briefing' and send it to my Telegram.
    """
    
    payload = {
        "message": query,
        "user_id": "test_user_integration",
        "reply_via_telegram": True,
        "telegram_chat_id": 916700879,
        "thread_id": f"weekly_prep_{datetime.now().strftime('%Y%j')}"
    }
    
    logger.info("🚀 Triggering Full Integration Test...")
    logger.info(f"Payload: {payload}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Integration Test Success!")
                logger.info(f"Response: {result.get('data', {}).get('response', '')[:200]}...")
            else:
                logger.error(f"❌ Integration Test Failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_integration_test())
