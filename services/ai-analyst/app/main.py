from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import traceback
from datetime import datetime
from pydantic import BaseModel

from app.schemas.analysis import MarketAnalysisRequest, JournalAnalysisRequest, AnalysisResponse
from app.services.gemini import GeminiClient
from app.utils.response import success_response
from app.services.rag import RAGService
from app.schemas.chat import StrategyChatRequest
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.agents.episodic_memory import EpisodicMemoryAgent
from app.agents.post_mortem import PostMortemAgent
from app.agents.entry_reason import EntryReasonAgent
from app.agents.trade_manager import TradeManagementAgent
from app.agents.risk_rebalancer import RiskRebalancerAgent
from app.services.sentiment import SentimentService
from app.core.bootstrap import bootstrap_tools
from app.routers import ingest, agents, admin, external, orchestration, knowledge, mri, risk
from app.routers import analysis as analysis_router
from app.services.memory import MemoryService
from app.services.episodic_memory import EpisodicMemoryService
from app.database import SessionLocal
from langgraph.checkpoint.redis import RedisSaver
from redis.asyncio import Redis
from app.core.scheduler import scheduler
from app.utils.scheduler_utils import with_tracing
from app.services.session_observer import session_observer
from app.services.stability_observer import stability_observer
from app.utils.state_cache import state_cache

# Setup Logging
from app.utils.middleware import setup_tracing_logging
logger = setup_tracing_logging()

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
    
    # 0. Infrastructure Pre-flight Check
    try:
        from redis.asyncio import Redis
        import os
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis = Redis.from_url(redis_url)
        modules = await redis.execute_command("MODULE LIST")
        module_names = [m[1].decode('utf-8') if isinstance(m[1], bytes) else m[1] for m in modules]
        
        required = ["search", "ReJSON"]
        missing = [m for m in required if m not in module_names]
        
        if missing:
            logger.error(f"❌ CRITICAL: Missing Redis Modules: {missing}")
            logger.error("👉 Please ensure you ARE NOT using 'command' override in docker-compose.yml for the redis service.")
            logger.error("🛑 Service will proceed with local MemorySaver, but cross-turn memory will be DISABLED.")
        else:
            logger.info(f"✅ Infrastructure Verified (Redis Modules: {module_names})")
        await redis.close()
    except Exception as e:
        logger.warning(f"⚠️ Infrastructure check skipped (Redis not ready): {e}")

    # Clear any stale services from global dict (important for reloads)
    for key in services.keys():
        services[key] = None

    # 1. Boostrap Redis (for Task State and Audit Logs)
    try:
        from redis.asyncio import Redis
        redis_bus = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
        services["redis"] = redis_bus
        logger.info("✅ Redis Message Bus Initialized")
    except Exception as e:
        logger.error(f"❌ Redis Initialization Failed: {e}")

    # 1b. Bootstrap Tools
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
            
            # Phase 5: Initialize Episodic Memory Service (pgvector)
            db = SessionLocal()
            services["episodic_memory_service"] = EpisodicMemoryService(db)
            logger.info("✅ Episodic Memory Service (pgvector) Ready")
    except Exception as e:
        logger.error(f"❌ Memory Services Failed: {e}")

    try:
        from app.services.skill import SkillService
        services["skill"] = SkillService()
        logger.info("✅ Skill Service Initialized")
    except Exception as e:
        logger.error(f"❌ Skill Service Failed: {e}")

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
                    memory_service=services.get("memory"),
                    post_mortem_agent=services.get("post_mortem"),
                    trade_manager_agent=services.get("trade_manager"),
                    risk_rebalancer_agent=services.get("risk_rebalancer"),
                    episodic_memory_service=services.get("episodic_memory_service")
                )
                logger.info("✅ Strategy Advisor Agent Ready")
        except Exception as e:
            logger.error(f"❌ Strategy Advisor Agent Failed: {e}")

        try:
            services["episodic_memory"] = EpisodicMemoryAgent()
            logger.info("✅ Episodic Memory Agent Ready")
        except Exception as e:
            logger.error(f"❌ Episodic Memory Agent Failed: {e}")

        try:
            if services["rag"]:
                from app.agents.skill_creator import SkillCreatorAgent
                services["skill_creator"] = SkillCreatorAgent(services["gemini"])
                logger.info("✅ Skill Creator Agent Ready")
                
                services["post_mortem"] = PostMortemAgent(services["gemini"], services["rag"])
                logger.info("✅ Post-Mortem Agent Ready")

                services["entry_reason"] = EntryReasonAgent(services["gemini"])
                logger.info("✅ Entry Reason Agent Ready")

                services["trade_manager"] = TradeManagementAgent(services["gemini"])
                logger.info("✅ Trade Management Agent Ready")

                services["risk_rebalancer"] = RiskRebalancerAgent(services["gemini"])
                logger.info("✅ Risk Rebalancer Agent Ready")
        except Exception as e:
            logger.error(f"❌ Skill Creator or Post-Mortem Agent Failed: {e}")
            logger.error(traceback.format_exc())

        try:
            services["sentiment"] = SentimentService()
            logger.info("✅ Sentiment Service Ready")
        except Exception as e:
            logger.error(f"❌ Sentiment Service Failed: {e}")

        try:
            from app.services.falkor import FalkorService
            services["falkor"] = FalkorService()
            # Note: Falkor connect is called on-demand or in lifespan if needed.
            # We lazy-connect in the service for now to avoid hard startup failures.
            logger.info("✅ Falkor Service (Knowledge Bridge) Initialized")
        except Exception as e:
            logger.error(f"❌ Falkor Service Failed: {e}")

        try:
            # Start Scheduler & Schedule Job
            scheduler.start()
            
            # Gold OI Drift Session Reports
            scheduler.add_job(with_tracing(session_observer.run_session_drift_report), 'cron', hour=8, minute=0, args=['London'], misfire_grace_time=3600)
            scheduler.add_job(with_tracing(session_observer.run_session_drift_report), 'cron', hour=13, minute=30, args=['New York'], misfire_grace_time=3600)
            
            # Gold Sentiment Analysis (Every 15 minutes)
            # Replaced with Sentiment-to-Risk Autonomous Pipeline
            from app.core.scheduler_tasks import check_sentiment_risk_drift
            scheduler.add_job(with_tracing(check_sentiment_risk_drift), 'interval', minutes=15, misfire_grace_time=600)
            
            # Predictor Stability Check (Every 15 minutes)
            scheduler.add_job(with_tracing(stability_observer.run_predictor_stability_check), 'interval', minutes=15, misfire_grace_time=300)
            
            # Daily Post-Mortem Analysis (01:00 UTC)
            from app.core.scheduler_tasks import run_daily_post_mortem
            scheduler.add_job(with_tracing(run_daily_post_mortem), 'cron', hour=1, minute=0, misfire_grace_time=3600)
            
            logger.info("✅ Scheduler Started (Guardian, Session, Sentiment, Stability & Post-Mortem Jobs Added)")
        except Exception as e:
            logger.error(f"❌ Scheduler/Session Observer Failed: {e}")
            
        # 4. Start StateCache (ECST)
        try:
            await state_cache.start()
            logger.info("✅ StateCache (ECST) Started")
        except Exception as e:
            logger.error(f"❌ StateCache Startup Failed: {e}")

        logger.info("\n" + "="*50)
        logger.info("✨ Service Startup Complete")
        logger.info("="*50 + "\n")
        
        yield
    
    logger.info("🛑 Service Shutdown Sequence Initiated...")
    
    # Trace why we are shutting down if possible
    import threading
    active_threads = threading.active_count()
    logger.info(f"📊 Shutdown Context: {active_threads} active threads remaining.")

    if services.get("sentiment"):
        try:
            await services["sentiment"].close()
            logger.info("✅ Sentiment Service Cleanup Complete")
        except Exception as e:
            logger.error(f"❌ Sentiment Service Cleanup Failed: {e}")
            
    if services.get("checkpointer"):
        # If it's a RedisSaver, we might want to ensure it's closed
        logger.info("✅ Checkpointer Cleanup Complete")

    await state_cache.stop()
    logger.info("✅ StateCache Cleanup Complete")

    logger.info("✨ Application Shutdown Finished.")

app = FastAPI(title="AI Analyst Service", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

from app.utils.middleware import RequestIDMiddleware
app.add_middleware(RequestIDMiddleware)

app.include_router(ingest.router, prefix="/api/v1/ai", tags=["Ingest"])
app.include_router(agents.router, prefix="/api/v1/ai", tags=["Agents"])
app.include_router(admin.router, prefix="/api/v1/ai/admin", tags=["Admin"])
app.include_router(external.router, prefix="/api/v1/ai/external", tags=["External"])
app.include_router(analysis_router.router, prefix="/api/v1", tags=["Analysis"]) 
app.include_router(orchestration.router, prefix="/api/v1", tags=["Orchestration"])
app.include_router(knowledge.router, prefix="/api/v1/ai", tags=["Knowledge"])
app.include_router(mri.router, prefix="/api/v1", tags=["MRI"])
app.include_router(risk.router, prefix="/api/v1/ai", tags=["Risk"])


@app.get("/health")
def health_check():
    data = {
        "status": "ok", 
        "service": "ai-analyst",
        "gemini": "active" if services["gemini"] else "inactive",
        "rag": "active" if services["rag"] else "inactive",
        "agents": {
            "strategy_advisor": "active" if services["strategy_advisor"] else "inactive",
            "sentiment_service": "active" if services["sentiment"] else "inactive",
            "risk_rebalancer": "active" if services["risk_rebalancer"] else "inactive"
        }
    }
    return success_response(data=data)
