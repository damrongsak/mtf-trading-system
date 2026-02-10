import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.tools.calendar import GetEconomicCalendarTool
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_calendar_tool():
    logger.info("=== Testing AI Analyst Calendar Tool (Redis Integration) ===")
    
    tool = GetEconomicCalendarTool()
    
    # We expect data to be in Redis from the previous data-pipeline test
    # If not, this test might fall back to API, which is also a valid test of the fallback logic.
    
    logger.info("[1] Calling tool._arun(currency='USD')...")
    try:
        result = await tool._arun(currency="USD", days=7)
        logger.info("✅ Tool execution completed.")
        print("\n--- Tool Output ---\n")
        print(result)
        print("\n-------------------\n")
        
        if "No economic events" in result and "Failed" not in result:
             logger.info("⚠️ returned no events (possible if cache empty and API empty), but didn't crash.")
        elif "Failed" in result:
             logger.error("❌ Tool returned failure message.")
        else:
             logger.info("✅ Tool returned formatted events.")

    except Exception as e:
        logger.error(f"❌ Tool execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_calendar_tool())
