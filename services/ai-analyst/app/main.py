from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import traceback
from datetime import datetime
from pydantic import BaseModel

from app.schemas.analysis import MarketAnalysisRequest, JournalAnalysisRequest, AnalysisResponse
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.schemas.chat import StrategyChatRequest
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.services.sentiment import SentimentService
from app.core.bootstrap import bootstrap_tools
from app.routers import ingest, agents
from app.routers import analysis as analysis_router
from app.services.memory import MemoryService
from langgraph.checkpoint.redis import RedisSaver
from redis import Redis

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-analyst")

from app.core.globals import services

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Handles service initialization and health checks.
    """
    logger.info("\n" + "="*50)
    logger.info("🚀 AI Analyst Service Starting...")
    logger.info("="*50 + "\n")

    # Clear any stale services from global dict (important for reloads)
    for key in services.keys():
        services[key] = None

    # 1. Bootstrap Tools
    try:
        bootstrap_tools()
        logger.info("✅ Tools Bootstrapped")
    except Exception as e:
        logger.error(f"❌ Failed to bootstrap tools: {e}")

    # 2. Initialize Core Services
    try:
        services["gemini"] = GeminiClient()
        logger.info("✅ Gemini Client Initialized")
    except Exception as e:
        logger.error(f"❌ Gemini Client Failed: {e}")

    try:
        services["rag"] = RAGService(services["gemini"])
        collections = services["rag"].qdrant.get_collections()
        logger.info(f"✅ Qdrant Connected (Collections: {len(collections.collections)})")
    except Exception as e:
        logger.error(f"❌ RAG Service/Qdrant Failed: {e}")

    try:
        if services["rag"]:
            services["memory"] = MemoryService(services["rag"])
            logger.info("✅ Memory Service (Long-Term) Ready")
    except Exception as e:
        logger.error(f"❌ Memory Service Failed: {e}")

    # 3. Handle Checkpointer and Agents within AsyncExitStack
    from contextlib import AsyncExitStack
    from langgraph.checkpoint.memory import MemorySaver
    
    # Default to MemorySaver
    services["checkpointer"] = MemorySaver()

    async with AsyncExitStack() as stack:
        # Try to upgrade to Redis for persistence
        try:
            from app.core.config import settings
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver
            
            logger.info(f"Connecting to Redis at: {settings.redis.url}")
            # IMPORTANT: AsyncRedisSaver.from_conn_string returns a CONTEXT MANAGER.
            # We MUST use stack.enter_async_context to get the actual checkpointer object.
            # This fixes the 'AttributeError: ... no attribute get_next_version'
            services["checkpointer"] = await stack.enter_async_context(
                AsyncRedisSaver.from_conn_string(settings.redis.url)
            )
            logger.info("✅ Redis Checkpointer (Short-Term Memory) Ready")
        except Exception as e:
            logger.warning(f"⚠️ Redis Checkpointer Failed ({e}). Falling back to MemorySaver.")
            services["checkpointer"] = MemorySaver()


        try:
            if services["rag"]:
                services["strategy_advisor"] = StrategyAdvisorAgent(
                    services["rag"], 
                    services["gemini"], 
                    checkpointer=services["checkpointer"],
                    memory_service=services.get("memory")
                )
                logger.info("✅ Strategy Advisor Agent Ready")
        except Exception as e:
            logger.error(f"❌ Strategy Advisor Agent Failed: {e}")


        try:
            services["sentiment"] = SentimentService()
            logger.info("✅ Sentiment Service Ready")
        except Exception as e:
            logger.error(f"❌ Sentiment Service Failed: {e}")

        logger.info("\n" + "="*50)
        logger.info("✨ Service Startup Complete")
        logger.info("="*50 + "\n")
        
        yield
    
    logger.info("🛑 Service Shutting Down...")
    if services.get("sentiment"):
        await services["sentiment"].close()
        logger.info("✅ Sentiment Service Cleanup Complete")

app = FastAPI(title="AI Analyst Service", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(ingest.router, prefix="/api/v1/ai/ingest", tags=["Ingest"])
app.include_router(agents.router, prefix="/api/v1/ai", tags=["Agents"])
app.include_router(analysis_router.router, prefix="/api/v1", tags=["Analysis"]) 


@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "service": "ai-analyst",
        "gemini": "active" if services["gemini"] else "inactive",
        "rag": "active" if services["rag"] else "inactive",
        "agents": {
            "strategy_advisor": "active" if services["strategy_advisor"] else "inactive",
            "sentiment_service": "active" if services["sentiment"] else "inactive"
        }
    }
