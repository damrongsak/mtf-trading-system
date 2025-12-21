from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.decision_log import DecisionLog
import logging
import asyncio

logger = logging.getLogger(__name__)

class AuditLogger:
    def __init__(self, component: str):
        self.component = component

    def log(self, action: str, tool_call: dict = None, outcome: dict = None, prompt_version: str = None):
        """
        Log a decision or action.
        This is synchronous but can be wrapped or called from thread.
        For high throughput, we might want to batch or use async DB driver.
        For now, we use brief sessions.
        """
        try:
            db = SessionLocal()
            entry = DecisionLog(
                component=self.component,
                action=action,
                tool_call=tool_call,
                outcome=outcome,
                prompt_version=prompt_version
            )
            db.add(entry)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    async def alog(self, action: str, tool_call: dict = None, outcome: dict = None, prompt_version: str = None):
        """Async wrapper for log"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.log, action, tool_call, outcome, prompt_version)

# Global instance for data-pipeline
audit_logger = AuditLogger(component="data-pipeline")
