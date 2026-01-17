from fastapi import APIRouter, HTTPException
from app.registry import StrategyRegistry
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["Strategies"])

@router.post("/reload")
def reload_strategies_endpoint():
    """
    Triggers a hot reload of all strategy plugins.
    Use this after adding or modifying strategy files.
    """
    try:
        success = StrategyRegistry.reload_strategies()
        return {"status": "success", "message": "Strategies reloaded successfully"}
    except Exception as e:
        logger.error(f"Failed to reload strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))
