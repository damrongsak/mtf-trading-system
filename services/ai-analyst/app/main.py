from fastapi import FastAPI, HTTPException
from app.schemas.analysis import MarketAnalysisRequest, JournalAnalysisRequest, AnalysisResponse
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from datetime import datetime

app = FastAPI(title="AI Analyst Service")

# Initialize services (Lazy loading could be better, but simple for now)
try:
    gemini_client = GeminiClient()
    rag_service = RAGService()
except Exception as e:
    print(f"Warning: Failed to initialize AI services: {e}")
    gemini_client = None
    rag_service = None

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

    insight = await gemini_client.analyze_journal_entry(request.entry_content, similar_entries)
    
    return AnalysisResponse(
        insight=insight,
        timestamp=datetime.utcnow().isoformat()
    )

