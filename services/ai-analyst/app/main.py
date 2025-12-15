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

from app.agents.market_observer import MarketObserverAgent
from pydantic import BaseModel

# ... imports ...

# Initialize services (Lazy loading could be better, but simple for now)
try:
    gemini_client = GeminiClient()
    rag_service = RAGService()
    # Initialize Agent
    market_observer = MarketObserverAgent()
except Exception as e:
    print(f"Warning: Failed to initialize AI services: {e}")
    gemini_client = None
    rag_service = None
    market_observer = None

# ... existing endpoints ...

class AgentRunRequest(BaseModel):
    input_text: str = "Generate a market situation report for XAU/USD."

@app.post("/agent/observer/run")
async def run_observer_agent(request: AgentRunRequest):
    if not market_observer:
        raise HTTPException(status_code=503, detail="AI Agent unavailable")
    
    try:
        report = await market_observer.run(request.input_text)
        return {"report": report, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "service": "ai-analyst",
        "gemini": "active" if gemini_client else "inactive",
        "rag": "active" if rag_service else "inactive"
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
            similar_entries = await rag_service.search_similar(request.entry_content)
        except Exception:
            pass # Fail gracefully on RAG for now

    insight = await gemini_client.analyze_journal_entry(request.entry_content, similar_entries, user_id=request.user_id)
    
    return AnalysisResponse(
        insight=insight,
        timestamp=datetime.utcnow().isoformat()
    )

