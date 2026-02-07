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
from app.agents.market_observer import MarketObserverAgent
from app.agents.daily_briefing import DailyBriefingAgent
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

    # 1. Bootstrap Tools
    try:
        bootstrap_tools()
        logger.info("✅ Tools Bootstrapped")
    except Exception as e:
        logger.error(f"❌ Failed to bootstrap tools: {e}")

    # 2. Initialize Gemini Client
    try:
        services["gemini"] = GeminiClient()
        # Simple health check (optional, e.g. checking models, but simple init is usually enough for validation)
        logger.info("✅ Gemini Client Initialized")
    except Exception as e:
        logger.error(f"❌ Gemini Client Failed: {e}")

    # 3. Initialize RAG Service (Qdrant)
    try:
        services["rag"] = RAGService(services["gemini"])
        # Check Qdrant Connection
        try:
             # The RAG service init already attempts to ensure collections, which effectively checks connection
             # We can explicitly list collections if we want to be sure
             collections = services["rag"].qdrant.get_collections()
             logger.info(f"✅ Qdrant Connected (Collections: {len(collections.collections)})")
        except Exception as e:
            logger.warning(f"⚠️ RAG Initialized but Qdrant check failed: {e}")
            
    except Exception as e:
        logger.error(f"❌ RAG Service Failed: {e}")

    # 4. Initialize Memory Service
    try:
        if services["rag"]:
            services["memory"] = MemoryService(services["rag"])
            logger.info("✅ Memory Service (Long-Term) Ready")
    except Exception as e:
        logger.error(f"❌ Memory Service Failed: {e}")

    # 5. Initialize Redis Checkpointer (Short-Term Memory)
    # 5. Initialize Redis Checkpointer (Short-Term Memory)
    try:
        from app.core.config import settings
        from langgraph.checkpoint.memory import MemorySaver # Local import safe here
        
        logger.info(f"Connecting to Redis at: {settings.redis.url}")
        redis_conn = Redis.from_url(settings.redis.url)
        services["checkpointer"] = RedisSaver(redis_conn)
        logger.info("✅ Redis Checkpointer (Short-Term Memory) Ready")
    except Exception as e:
        logger.warning(f"⚠️ Redis Checkpointer Failed: {e}. Falling back to MemorySaver.")
        from langgraph.checkpoint.memory import MemorySaver
        services["checkpointer"] = MemorySaver()
        logger.info("✅ MemorySaver (In-Memory Checkpointer) Ready")

    # 6. Initialize Agents
    try:
        services["market_observer"] = MarketObserverAgent()
        logger.info("✅ Market Observer Agent Ready")
    except Exception as e:
        logger.error(f"❌ Market Observer Agent Failed: {e}")
    except Exception as e:
        logger.error(f"❌ Market Observer Agent Failed: {e}")

    try:
        if services["rag"]:
            # Pass checkpointer to agent
            services["strategy_advisor"] = StrategyAdvisorAgent(
                services["rag"], 
                services["gemini"], 
                checkpointer=services.get("checkpointer"),
                memory_service=services.get("memory")
            )
            logger.info("✅ Strategy Advisor Agent Ready")
        else:
            logger.warning("⚠️ Strategy Advisor Skipped (RAG missing)")
    except Exception as e:
        logger.error(f"❌ Strategy Advisor Agent Failed: {e}")

    try:
        services["daily_briefing"] = DailyBriefingAgent()
        logger.info("✅ Daily Briefing Agent Ready")
    except Exception as e:
        logger.error(f"❌ Daily Briefing Agent Failed: {e}")

    try:
        services["sentiment"] = SentimentService()
        if services["sentiment"]:
             logger.info("✅ Sentiment Service Ready (delegated to Data Pipeline)")
    except Exception as e:
        logger.error(f"❌ Sentiment Service Failed: {e}")

    logger.info("\n" + "="*50)
    logger.info("✨ Service Startup Complete")
    logger.info("="*50 + "\n")
    
    yield
    
    logger.info("🛑 Service Shutting Down...")

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
            "market_observer": "active" if services["market_observer"] else "inactive",
            "strategy_advisor": "active" if services["strategy_advisor"] else "inactive",
            "daily_briefing": "active" if services["daily_briefing"] else "inactive",
            "sentiment_service": "active" if services["sentiment"] else "inactive"
        }
    }
