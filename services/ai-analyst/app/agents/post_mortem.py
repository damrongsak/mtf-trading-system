import logging
import uuid

import json
import asyncio
from typing import List, Dict, Any, Optional
from app.services.gemini import GeminiClient
from app.services.rag import RAGService

from app.utils.json import safe_json_dumps
from app.models.trade import PostMortem
from app.database import SessionLocal

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
        # --- Phase 69: Hardening - Support Nested Trade Data ---
        actual_data = trade_data.get("trade", trade_data) if isinstance(trade_data, dict) else trade_data
        
        logger.info(f"🛡️ Post-Mortem Specialist: Received actual_data with keys: {list(actual_data.keys()) if isinstance(actual_data, dict) else 'Unknown'}")
        
        trade_id = actual_data.get("trade_id") or actual_data.get("id") or actual_data.get("order_id")
        logger.info(f"🛡️ Post-Mortem Specialist: Identified trade_id: {trade_id}")
        
        symbol = actual_data.get("symbol")
        
        # Serialize trade_data safely (handles UUIDs, Decimals, etc.)
        try:
            trade_json = safe_json_dumps(trade_data, indent=2)
        except Exception as e:
            logger.error(f"Failed to serialize trade data for {trade_id}: {e}")
            trade_json = str(trade_data) # Fallback to string representation

        prompt = f"""
        You are the 'Institutional Post-Mortem Agent' for MTF Olympus.
        Analyze the following closed trade and provide a deep behavioral and technical analysis.
        
        **Trade Details (Institutional Metrics):**
        {trade_json}
        
        **Analyze the following:**
        1. **Execution Quality**: Look at `execution_latency_ms` and `slippage_pips`. Was the broker execution optimal?
        2. **Profit Efficiency**: Compare `pnl_usd` with `risk_usd`.
        3. **Behavioral Classification**: Was this a 'Good Win' (followed plan), 'Bad Win' (luck, strayed from plan), 'Good Loss' (controlled risk, hit SL), or 'Bad Loss' (revenge trading, huge slippage, no SL)?
        4. **Institutional Metric - Profit Efficiency**: (Net PnL / Risk USD).
        
        **Output JSON only:**
        {{
            "classification": "GOOD_WIN|BAD_WIN|GOOD_LOSS|BAD_LOSS",
            "summary": "High-level summary of the trade outcome",
            "execution_quality_text": "Brief technical analysis of execution and slippage",
            "psychological_analysis": "Insight into the trader/algo behavior",
            "alpha_lesson": "Brief, actionable sentence for future retrieval",
            "metrics": {{
                "slippage_pips": 0.0,
                "execution_latency_ms": 0.0,
                "profit_efficiency": 0.0
            }},
            "smart_score": 0-100
        }}
        """
        
        try:
            response = await self.gemini.generate_content(
                model=[self.gemini.model_id, "gemini-2.5-flash", "gemini-2.0-flash"],
                contents=[prompt],
                config={"response_mime_type": "application/json"}
            )
            
            analysis = json.loads(response.get("text", "{}"))
            logger.info(f"Post-Mortem for {trade_id}: {analysis.get('classification')}")
            
            # --- Persist to Database ---
            try:
                logger.info(f"DB: Attempting to persist Post-Mortem for {trade_id}")
                db = SessionLocal()
                try:
                    # Check if already exists
                    # Ensure trade_id is a UUID object for SQLAlchemy
                    db_trade_id = trade_id
                    if isinstance(db_trade_id, str):
                        try:
                            db_trade_id = uuid.UUID(db_trade_id)
                        except ValueError:
                            logger.error(f"DB: Invalid UUID string {db_trade_id}")
                            pass
                            
                    existing = db.query(PostMortem).filter(PostMortem.trade_id == db_trade_id).first()
                    if existing:
                        pm = existing
                        logger.info(f"DB: Updating existing Post-Mortem for {trade_id}")
                    else:
                        pm = PostMortem(trade_id=db_trade_id)
                        db.add(pm)
                        logger.info(f"DB: Creating new Post-Mortem for {trade_id}")
                    
                    metrics = analysis.get("metrics", {})
                    pm.summary = analysis.get("summary")
                    pm.classification = analysis.get("classification")
                    pm.execution_quality = analysis.get("execution_quality_text")
                    pm.psychological_analysis = analysis.get("psychological_analysis")
                    pm.alpha_lesson = analysis.get("alpha_lesson")
                    pm.slippage_pips = float(metrics.get("slippage_pips", 0.0))
                    pm.execution_latency_ms = float(metrics.get("execution_latency_ms", 0.0))
                    pm.profit_efficiency = float(metrics.get("profit_efficiency", 0.0))
                    pm.pnl_net = float(actual_data.get("pnl_usd", 0.0) or actual_data.get("result_pnl", 0.0) or actual_data.get("profit", 0.0))
                    pm.smart_score = int(analysis.get("smart_score", 0))
                    
                    db.commit()
                    logger.info(f"✅ DB: Successfully saved Post-Mortem for {trade_id}")
                finally:
                    db.close()
            except Exception as db_err:
                logger.error(f"❌ DB ERROR: Failed to persist post-mortem for {trade_id}: {db_err}", exc_info=True)

            # Store in Qdrant as Lesson Learned (Legacy support)
            if analysis.get("alpha_lesson"):
                lesson_text = f"Result: {analysis['classification']} | Symbol: {symbol} | Lesson: {analysis['alpha_lesson']}"
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
