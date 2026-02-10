import asyncio
import httpx
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for AI Analyst (Internal)
BASE_URL = "http://localhost:8000/api/v1/ai"

async def test_flow(name, endpoint, method="POST", payload=None, headers=None):
    logger.info(f"--- Testing Flow: {name} ---")
    url = f"{BASE_URL}{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            if method == "POST":
                resp = await client.post(url, json=payload, headers=headers, timeout=180.0)
            else:
                resp = await client.get(url, headers=headers, timeout=180.0)
            
            if resp.status_code == 200:
                logger.info(f"✅ {name} Success (200)")
                # logger.info(f"Response: {json.dumps(resp.json(), indent=2)}")
                data = resp.json()
                report = data.get("report") or data.get("response")
                thoughts = data.get("thoughts")
                logger.info(f"Thoughts: {thoughts}")
                print(f"\nResponse Summary:\n{str(report)[:500]}...\n")
            else:
                logger.error(f"❌ {name} Failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"❌ {name} Exception: {e}")

async def run_tests():
    # 1. Market Scan Flow
    await test_flow(
        "Market Scan (Observer)", 
        "/agent/observer/run", 
        payload={"input_text": "Generate a market situation report for XAU/USD."}
    )
    
    # 2. Daily Briefing Flow
    # Note: This will likely have empty account data if no valid auth, 
    # but we check if the flow itself works.
    await test_flow(
        "Daily Briefing", 
        "/agent/briefing"
    )
    
    # 3. Standard Chat Flow
    await test_flow(
        "Standard Strategy Chat", 
        "/chat/sessions/message", 
        payload={
            "message": "What is the current risk management policy?",
            "user_id": "test_user_123"
        }
    )

if __name__ == "__main__":
    asyncio.run(run_tests())
