from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas.analysis import MarketAnalysisRequest, JournalAnalysisRequest, AnalysisResponse
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from datetime import datetime

app = FastAPI(title="AI Analyst Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

from app.schemas.chat import StrategyChatRequest
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.agents.market_observer import MarketObserverAgent
from app.agents.daily_briefing import DailyBriefingAgent
from app.services.sentiment import SentimentService
from pydantic import BaseModel
import traceback

class AgentRunRequest(BaseModel):
    input_text: str = "Generate a market situation report for XAU/USD."

class AnalysisRequest(BaseModel):
    symbol: str = "XAU/USD"
    context: str = ""

@app.post("/analyze/sentiment")
async def analyze_sentiment(req: AnalysisRequest):
    if not sentiment_service:
        raise HTTPException(status_code=503, detail="Sentiment Service unavailable (Check NewsAPI Key)")
    return await sentiment_service.get_sentiment(req.symbol)

# Initialize Services
gemini_client = None
rag_service = None
market_observer = None
strategy_advisor = None
daily_briefing = None
sentiment_service = None

try:
    gemini_client = GeminiClient()
except Exception as e:
    print(f"Warning: Failed to initialize GeminiClient: {e}")

try:
    rag_service = RAGService(gemini_client)
except Exception as e:
    print(f"Warning: Failed to initialize RAGService: {e}")

try:
    market_observer = MarketObserverAgent()
except Exception as e:
    print(f"Warning: Failed to initialize MarketObserverAgent: {e}")

try:
    if rag_service:
        strategy_advisor = StrategyAdvisorAgent(rag_service)
except Exception as e:
    print(f"Warning: Failed to initialize StrategyAdvisorAgent: {e}")

try:
    daily_briefing = DailyBriefingAgent()
except Exception as e:
    print(f"Warning: Failed to initialize DailyBriefingAgent: {e}")

try:
    sentiment_service = SentimentService()
except Exception as e:
    print(f"Warning: Failed to initialize SentimentService: {e}")

# ... existing endpoints ...

@app.post("/agent/observer/run")
async def run_observer_agent(request: AgentRunRequest):
    if not market_observer:
        raise HTTPException(status_code=503, detail="AI Agent unavailable")
    
    try:
        report = await market_observer.run(request.input_text)
        return {"report": report, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        print(f"Error executing agent: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/briefing")
async def run_daily_briefing():
    if not daily_briefing:
        raise HTTPException(status_code=503, detail="Daily Briefing Agent unavailable")
    
    try:
        report = await daily_briefing.run("Generate valid Daily Briefing.")
        return {"report": report, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        print(f"Error executing agent: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
async def chat_strategy(request: StrategyChatRequest):
    """
    Chat with the Strategy Advisor Agent regarding a specific strategy.
    """
    if not strategy_advisor:
        raise HTTPException(status_code=503, detail="Strategy Advisor Agent unavailable (Check Gemini/Qdrant config)")
    
    try:
        response_text = await strategy_advisor.run(
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
        "gemini": "active" if gemini_client else "inactive",
        "rag": "active" if rag_service else "inactive",
        "agents": {
            "market_observer": "active" if market_observer else "inactive",
            "strategy_advisor": "active" if strategy_advisor else "inactive",
            "daily_briefing": "active" if daily_briefing else "inactive",
            "sentiment_service": "active" if sentiment_service and sentiment_service.news_api_key else "inactive"
        }
    }

@app.post("/analyze/market", response_model=AnalysisResponse)
async def analyze_market(request: MarketAnalysisRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="AI Service unavailable")
    
    context = request.model_dump()
    insight = await gemini_client.generate_market_outlook(context)
    
    return AnalysisResponse(
        insight=insight,
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/analyze/journal", response_model=AnalysisResponse)
async def analyze_journal(request: JournalAnalysisRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="AI Service unavailable")

    # RAG Step: Find similar entries
    similar_entries = []
    if rag_service:
        try:
            # Legacy method call, ensuring compatibility if rag.py changed
            similar_entries = await rag_service.search_similar_entries(request.entry_content, user_id=request.user_id)
        except Exception as e:
             print(f"RAG search failed: {e}")

    insight = await gemini_client.analyze_journal_entry(request.entry_content, similar_entries, user_id=request.user_id)
    
    return AnalysisResponse(
        insight=insight,
        timestamp=datetime.utcnow().isoformat()
    )


