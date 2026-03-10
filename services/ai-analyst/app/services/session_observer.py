import logging
import asyncio
from typing import Optional
from app.core.globals import services
from app.tools.oi_drift import OpenInterestDriftTool
from app.services.telegram import send_telegram_message

logger = logging.getLogger(__name__)

class SessionObserver:
    """
    Automates institutional analysis at major market session opens.
    """
    
    def __init__(self):
        self.drift_tool = OpenInterestDriftTool()
        
    async def run_session_drift_report(self, session_name: str):
        """
        Executes a Gold OI Drift analysis and logs/broadcasts the results.
        """
        logger.info(f"🌞 Running {session_name} Session DRIFT Analysis...")
        
        try:
            # Run the drift analysis tool
            # Note: run() handles snapshot retrieval automatically
            report = await self.drift_tool.arun()
            
            # Log the full report
            logger.info(f"📊 {session_name} SESSION DRIFT REPORT:\n{report}")
            
            # Broadcast to Telegram if configured
            # In a real scenario, we'd have a default channel or user-specific chat_id
            # For now, we log it. If settings had a DEFAULT_CHAT_ID, we'd use it:
            # await send_telegram_message(settings.DEFAULT_CHAT_ID, f"📢 *{session_name} Open Analysis*\n\n{report}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Session Drift Report Failed ({session_name}): {e}")
            return None

# Singleton instance for the scheduler
session_observer = SessionObserver()
