import logging
import json
from typing import Dict, Any, Optional
from app.services.gemini import GeminiClient
from app.utils.json import safe_json_dumps

logger = logging.getLogger(__name__)

class EntryReasonAgent:
    """
    Analyzes the 'Why' behind a new trade entry.
    Captures the trader's (or bot's) intent and logic at the moment of execution.
    """
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    async def summarize_reason(self, trade_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Summarizes the entry logic and assigns a conviction score.
        """
        trade_id = trade_data.get("id") or trade_data.get("trace_id")
        
        try:
            trade_json = safe_json_dumps(trade_data, indent=2)
        except Exception as e:
            logger.error(f"Failed to serialize trade data for entry {trade_id}: {e}")
            trade_json = str(trade_data)

        prompt = f"""
        You are the 'Entry Reason Agent' for MTF Olympus.
        Analyze the following trade entry and summarize its technical/sentimental rationale.
        
        **Trade Details:**
        {trade_json}
        
        **Your Goal:**
        Extract the 'Core Logic' (e.g., SMC displacement, BB squeeze, News fade).
        Assess the conviction based on the provided strategy parameters and metadata.
        
        **Output JSON only:**
        {{
            "core_logic": "Brief technical summary",
            "conviction_score": 0-100,
            "key_confluence": ["List", "of", "factors"],
            "primary_risk": "What could invalidate this setup immediately?"
        }}
        """
        
        try:
            response = await self.gemini.generate_content(
                model=[self.gemini.model_id, "gemini-2.5-flash", "gemini-2.0-flash"],
                contents=[prompt],
                config={"response_mime_type": "application/json"}
            )
            
            analysis = json.loads(response.get("text", "{}"))
            logger.info(f"Entry Reason for {trade_id}: conviction={analysis.get('conviction_score')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Entry Reason analysis failed for trade {trade_id}: {e}")
            return None
