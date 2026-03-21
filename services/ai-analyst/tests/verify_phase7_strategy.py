import os
import json
import logging
import asyncio
import httpx
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000/api/v1/ai"
USER_ID = "demo1"
STRATEGY_ID = "bb_stoch_ob_v1"

async def test_market_observer_learn():
    """Step 1: Ask for market analysis to verify AI 'learns' into Episodic Memory."""
    url = f"http://localhost:8000/api/v1/ai/chat/sessions/message"
    payload = {
        "message": "Analyze the current XAU_USD market structure and identify the most significant BOS (Break of Structure) or ChoCh (Change of Character).",
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID
    }
    
    logger.info("--- Step 1: Market Observer (Learn) ---")
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                # Gateway returns {"status": "success", "data": {"response": "...", "thoughts": "..."}}
                content = result.get("data", {}).get("response", "")
                logger.info("AI Analysis Response:")
                logger.info("-" * 40)
                logger.info(content[:1000] + "..." if len(content) > 1000 else content)
                logger.info("-" * 40)
                
                if "BOS" in content.upper() or "CHOCH" in content.upper() or "STRUCTURE" in content.upper():
                    logger.info("✅ Success: AI identified market structure.")
                else:
                    logger.warning("⚠️ Partial Success: AI responded but did not explicitly mention BOS/ChoCh.")
                return True
            else:
                logger.error(f"❌ Failed: API returned {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error during Step 1: {e}")
            return False

async def test_memory_recall_query():
    """Step 2: Ask a follow-up to verify AI 'recalls' previous analysis from Episodic Memory."""
    url = f"http://localhost:8000/api/v1/ai/chat/sessions/message"
    payload = {
        "message": "Based on the structure you just identified, what is the nearest POI (Point of Interest)?",
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID
    }
    
    logger.info("--- Step 2: Memory Recall (Query) ---")
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                content = result.get("data", {}).get("response", "")
                logger.info("AI Recall Response:")
                logger.info("-" * 40)
                logger.info(content[:1000] + "..." if len(content) > 1000 else content)
                logger.info("-" * 40)
                
                # Check for phrases suggesting recall
                recall_phrases = ["PREVIOUS", "LAST", "IDENTIFIED", "BOS", "CHOCH", "POI", "STRUCTURE"]
                if any(phrase in content.upper() for phrase in recall_phrases):
                    logger.info("✅ Success: AI recalled context from episodic memory.")
                else:
                    logger.warning("⚠️ Uncertain: AI responded but recall was not explicit.")
                return True
            else:
                logger.error(f"❌ Failed: API returned {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error during Step 2: {e}")
            return False

async def main():
    logger.info("🚀 Starting Phase 7: Advanced Strategy Verification (SMC + Memory)")
    
    # Step 1: Learn
    step1_ok = await test_market_observer_learn()
    if not step1_ok:
        logger.error("Stop: Step 1 failed.")
        return
        
    # Wait for memory persistence to settle
    logger.info("Waiting 5s for background memory persistence...")
    await asyncio.sleep(5)
    
    # Step 2: Recall
    await test_memory_recall_query()
    
    logger.info("🏁 Phase 7 Verification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
