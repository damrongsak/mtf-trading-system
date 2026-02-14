import asyncio
import logging
from app.services.session_observer import session_observer
from app.core.globals import services
from app.services.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-observer")

async def test_observer():
    logger.info("Starting SessionObserver Manual Test...")
    
    # Mock necessary services if needed by the tool
    if not services.get("gemini"):
        services["gemini"] = GeminiClient()
        logger.info("Gemini Client Mocked")

    # Run the report
    report = await session_observer.run_session_drift_report("MANUAL_TEST")
    
    if report:
        logger.info("✅ Test Report Generated Successfully:")
        print(f"\n{report}\n")
    else:
        logger.error("❌ Test Report Failed")

if __name__ == "__main__":
    asyncio.run(test_observer())
