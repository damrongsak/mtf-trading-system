import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.core.config import settings

from app.utils.json import safe_json_dumps

logger = logging.getLogger(__name__)

class PostMortemAgent:
    """
    Analyzes closed trades to extract "Institutional Wisdom".
    Evolves the system based on wins and losses.
    """
    def __init__(self, gemini_client: GeminiClient, rag_service: RAGService):
        self.gemini = gemini_client
        self.rag = rag_service

    async def analyze_trade(self, trade_data: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
        """
        Runs a post-mortem analysis on a single closed trade.
        """
        trade_id = trade_data.get("id") or trade_data.get("order_id")
        symbol = trade_data.get("symbol")
        result = trade_data.get("result_pnl", 0)
        
        # Serialize trade_data safely (handles UUIDs, Decimals, etc.)
        try:
            trade_json = safe_json_dumps(trade_data, indent=2)
        except Exception as e:
            logger.error(f"Failed to serialize trade data for {trade_id}: {e}")
            trade_json = str(trade_data) # Fallback to string representation

        prompt = f"""
        You are the 'Post-Mortem Agent' for MTF Olympus.
        Analyze the following closed trade and extract ONE critical lesson learned.
        
        **Trade Details:**
        {trade_json}
        
        **Your Goal:**
        Be brutally clinical. Was this a 'Good Win', 'Bad Win', 'Good Loss' (followed plan), or 'Bad Loss'?
        Identify if there was a logic failure, emotional interference, or market regime shift.
        
        **Output JSON only:**
        {{
            "classification": "GOOD_WIN|BAD_WIN|GOOD_LOSS|BAD_LOSS",
            "critical_lesson": "Brief, actionable sentence for future retrieval",
            "technical_error": "None or specific technical reason",
            "psychological_factor": "Optional insight",
            "smart_score": 0-100
        }}
        """
        
        try:
            response = await self.gemini.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt],
                config={"response_mime_type": "application/json"}
            )
            
            analysis = json.loads(response.get("text", "{}"))
            logger.info(f"Post-Mortem for {trade_id}: {analysis.get('classification')}")
            
            # Store in Qdrant as Lesson Learned
            if analysis.get("critical_lesson"):
                lesson_text = f"Result: {analysis['classification']} | Symbol: {symbol} | Lesson: {analysis['critical_lesson']}"
                await self.rag.ingest_lesson_learned(
                    lesson_id=f"pm_{trade_id}",
                    content=lesson_text,
                    trade_id=str(trade_id),
                    user_id=user_id,
                    metadata=analysis
                )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Post-Mortem analysis failed for trade {trade_id}: {e}")
            return None

    async def run_batch_analysis(self, trades: List[Dict[str, Any]], user_id: str):
        """Analyze a list of trades."""
        tasks = [self.analyze_trade(t, user_id) for t in trades]
        return await asyncio.gather(*tasks)
