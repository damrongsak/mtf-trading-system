from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
import logging
from app.core.globals import services
from app.utils.response import success_response
from app.schemas.mri import CoachingRequest, CoachingResponse

router = APIRouter(prefix="/ai/mri", tags=["MRI"])
logger = logging.getLogger(__name__)

@router.post("/coaching", response_model=CoachingResponse)
async def get_psychological_mri(
    request: CoachingRequest,
    authorization: Optional[str] = Header(None)
):
    """
    RAG-driven psychological coaching node. 
    Analyzes journal patterns and market context to provide actionable advice.
    """
    try:
        gemini = services.get("gemini")
        if not gemini:
            raise HTTPException(status_code=503, detail="Gemini service unavailable")

        # 1. Fetch Context using JournalMRITool logic directly or via tool registry
        from app.tools.journal_mri import JournalMRITool
        mri_tool = JournalMRITool()
        context = await mri_tool.run_tool(
            {"lookback_days": request.lookback_days, "limit": 10},
            auth_token=authorization
        )

        if "No recent journal entries" in context:
            return CoachingResponse(
                psychological_state="NEUTRAL",
                advice="I don't see enough recent journal entries to perform a deep MRI. Start logging your emotions and mistakes to unlock coaching.",
                suggested_actions=["Log at least 3 trades with Mental State notes"]
            )

        # 2. Generate Coaching via Gemini
        prompt = f"""
        You are the 'Institutional Trading Psychologist' for MTF Olympus.
        Your goal is to perform a 'Psychological MRI' on the following trader reflections:
        
        TRADER CONTEXT:
        {context}
        
        TASK:
        1. Identify the primary psychological state (e.g., Revenge Trading, FOMO, over-confidence, or high discipline).
        2. Provide specific, actionable coaching advice in Thai or English (match the trader's suspected preference, or provide both).
        3. Suggest 2-3 behavioral corrections.
        
        FORMAT: Return a clean narrative.
        """
        
        # Use the configured model from settings
        response = await gemini.generate_content(
            model=gemini.model_id,
            contents=[prompt]
        )
        
        # Extract text from the response dict
        response_text = response.get("text", "No coaching advice generated.")
        
        # Simple extraction for MVP (In prod we would use structured output)
        return CoachingResponse(
            psychological_state="ANALYZED",
            advice=response_text,
            suggested_actions=["Review your last 3 losses", "Wait for H1 BOS confirmation"],
            sentiment_trend="STABLE"
        )

    except Exception as e:
        logger.error(f"MRI Coaching Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
