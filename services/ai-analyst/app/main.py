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

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-analyst")

# Global Service Instances
services = {
    "gemini": None,
    "rag": None,
    "market_observer": None,
    "strategy_advisor": None,
    "daily_briefing": None,
    "sentiment": None
}

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

    # 4. Initialize Agents
    try:
        services["market_observer"] = MarketObserverAgent()
        logger.info("✅ Market Observer Agent Ready")
    except Exception as e:
        logger.error(f"❌ Market Observer Agent Failed: {e}")

    try:
        if services["rag"]:
            services["strategy_advisor"] = StrategyAdvisorAgent(services["rag"], services["gemini"])
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
    # Cleanup logic if needed

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


class AgentRunRequest(BaseModel):
    input_text: str = "Generate a market situation report for XAU/USD."

class AnalysisRequest(BaseModel):
    symbol: str = "XAU/USD"
    context: str = ""

@app.post("/analyze/sentiment")
async def analyze_sentiment(req: AnalysisRequest):
    if not services["sentiment"]:
        raise HTTPException(status_code=503, detail="Sentiment Service unavailable")
    return await services["sentiment"].get_sentiment(req.symbol)


@app.post("/agent/observer/run")
async def run_observer_agent(request: AgentRunRequest, authorization: str = Header(None, alias="Authorization")):
    if not services["market_observer"]:
        raise HTTPException(status_code=503, detail="AI Agent unavailable")
    
    try:
        report = await services["market_observer"].run(request.input_text, auth_header=authorization)
        return {"report": report, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        print(f"Error executing agent: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/briefing")
async def run_daily_briefing(authorization: str = Header(None, alias="Authorization")):
    if not services["daily_briefing"]:
        raise HTTPException(status_code=503, detail="Daily Briefing Agent unavailable")
    
    try:
        report = await services["daily_briefing"].run("Generate valid Daily Briefing.", auth_header=authorization)
        return {"report": report, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        print(f"Error executing agent: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/chat/sessions/message")
async def chat_strategy(request: StrategyChatRequest):
    """
    Chat with the Strategy Advisor Agent regarding a specific strategy.
    """
    if not services["strategy_advisor"]:
        raise HTTPException(status_code=503, detail="Strategy Advisor Agent unavailable (Check Gemini/Qdrant config)")
    
    try:
        response_text = await services["strategy_advisor"].run(
            input_text=request.message, 
            user_id=request.user_id,
            context_code=request.context_code,
            image_b64=request.image_b64
        )
        return {
            "response": response_text,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error in strategy chat: {str(e)}")
        traceback.print_exc()
        # Fallback error response properly formatted
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

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

@app.post("/analyze/market", response_model=AnalysisResponse)
async def analyze_market(request: MarketAnalysisRequest):
    if not services["gemini"]:
        raise HTTPException(status_code=503, detail="AI Service unavailable")
    
    context = request.model_dump()
    insight = await services["gemini"].generate_market_outlook(context)
    
    return AnalysisResponse(
        insight=insight,
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/analyze/journal", response_model=AnalysisResponse)
async def analyze_journal(request: JournalAnalysisRequest):
    if not services["gemini"]:
        raise HTTPException(status_code=503, detail="AI Service unavailable")

    # RAG Step: Find similar entries
    similar_entries = []
    if services["rag"]:
        try:
            # Legacy method call, ensuring compatibility if rag.py changed
            similar_entries = await services["rag"].search_similar_entries(request.entry_content, user_id=request.user_id)
        except Exception as e:
             print(f"RAG search failed: {e}")

    insight = await services["gemini"].analyze_journal_entry(request.entry_content, similar_entries, user_id=request.user_id)
    
    return AnalysisResponse(
        insight=insight,
        timestamp=datetime.utcnow().isoformat()
    )

class SMCNarrativeRequest(BaseModel):
    smc_data: dict
    price_context: dict

@app.post("/analyze/smc-narrative", response_model=AnalysisResponse)
async def analyze_smc_narrative(request: SMCNarrativeRequest):
    if not services["gemini"]:
        raise HTTPException(status_code=503, detail="AI Service unavailable")
    
    insight = await services["gemini"].generate_smc_narrative(request.smc_data, request.price_context)
    
    return AnalysisResponse(
        insight=insight,
        timestamp=datetime.utcnow().isoformat()
    )
