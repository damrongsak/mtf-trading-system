import asyncio
import httpx
import json
import logging
import sys
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for AI Analyst (Internal Loopback)
BASE_URL = "http://127.0.0.1:8000/api/v1/ai"
HEALTH_URL = "http://127.0.0.1:8000/health"

async def wait_for_service(max_retries=120):
    logger.info("Waiting for service to become healthy...")
    async with httpx.AsyncClient() as client:
        for i in range(max_retries):
            try:
                resp = await client.get(HEALTH_URL, timeout=2.0)
                if resp.status_code == 200:
                    logger.info("✅ Service is HEALTHY.")
                    return True
            except:
                pass
            if i % 10 == 0:
                logger.info(f"Still waiting... ({i}/{max_retries})")
            await asyncio.sleep(2)
    return False

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
                data = resp.json()
                report = data.get("report") or data.get("response")
                # thoughts = data.get("thoughts")
                # if thoughts: logger.info(f"Thoughts: {str(thoughts)[:200]}...")
                print(f"\nResponse Summary:\n{str(report)[:500]}...\n")
            else:
                logger.error(f"❌ {name} Failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"❌ {name} Exception: {e}")

async def run_tests():
    if not await wait_for_service():
        logger.error("❌ Service failed to become healthy. Aborting tests.")
        return

    # 1. Market Scan Flow
    await test_flow(
        "Market Scan (Observer)", 
        "/agent/observer/run", 
        payload={"input_text": "Generate a market situation report for XAU/USD."}
    )
    
    # 2. Daily Briefing Flow
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
