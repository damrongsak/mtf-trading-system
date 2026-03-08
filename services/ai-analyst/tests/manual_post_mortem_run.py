import asyncio
import logging
import sys
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.agents.post_mortem import PostMortemAgent
from app.core.globals import services
from app.core.scheduler_tasks import run_daily_post_mortem

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manual_post_mortem")

async def main():
    logger.info("🚀 Starting Manual Post-Mortem Run...")
    
    # 1. Initialize Services
    gemini = GeminiClient()
    rag = RAGService(gemini)
    post_mortem_agent = PostMortemAgent(gemini, rag)
    
    # 2. Populate Globals
    services["gemini"] = gemini
    services["rag"] = rag
    services["post_mortem"] = post_mortem_agent
    
    # 3. Run Task
    # Note: run_daily_post_mortem fetches trades from last 24h.
    # To ensure we find some, let's manually adjust the 'yesterday' in a more flexible way if needed,
    # but the 436 trades might have some recent ones.
    await run_daily_post_mortem()
    
    logger.info("✨ Manual Run Complete")

if __name__ == "__main__":
    asyncio.run(main())
