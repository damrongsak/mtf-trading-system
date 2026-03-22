from fastapi import APIRouter, HTTPException, Path
from app.registry import StrategyRegistry
from app.fleet import FleetManager
from app.market_data import market_data_manager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["Strategies"])

@router.get("")
def list_strategies():
    """Returns all discovered strategy templates."""
    return StrategyRegistry.list_templates()

@router.get("/active")
def list_active_fleet():
    """Returns all currently running strategy instances in the fleet."""
    fleet = FleetManager.get_instance()
    # Filter out the 'logic' function for JSON serialization
    active = {}
    for sid, ctx in fleet.active_strategies.items():
        copy = ctx.copy()
        copy.pop("logic", None)
        active[sid] = copy
    
    deployments = {}
    for did, ctx in fleet.active_deployments.items():
        copy = ctx.copy()
        copy.pop("executor", None)
        deployments[did] = copy
        
    return {
        "templates": active,
        "deployments": deployments
    }

@router.post("/reload")
def reload_strategies_endpoint():
    """
    Triggers a hot reload of all strategy plugins.
    Use this after adding or modifying strategy files.
    """
    try:
        success = StrategyRegistry.reload_strategies()
        # Also reload fleet to sync with DB
        import asyncio
        asyncio.create_task(FleetManager.get_instance().load_fleet())
        return {"status": "success", "message": "Strategies reloaded successfully"}
    except Exception as e:
        logger.error(f"Failed to reload strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{strategy_id}/tick")
async def trigger_manual_tick(strategy_id: str = Path(..., description="ID of the active template strategy")):
    """
    Manually triggers a logic tick for an active strategy instance.
    """
    fleet = FleetManager.get_instance()
    context = fleet.active_strategies.get(strategy_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"Active strategy {strategy_id} not found in fleet.")
    
    try:
        # Re-using the StrategyState wrapper pattern from FleetManager.tick()
        class StrategyState:
            def __init__(self, ctx):
                self.config_json = ctx["config"]
                self.symbol = ctx["symbol"]
                self.id = ctx["id"]
                self.fund_id = ctx.get("fund_id")
                self.broker_account_id = ctx["broker_account_id"]
                self.timeframe = ctx["config"].get("tf_trigger", "15min") # Fallback to trigger tf
        
        state_obj = StrategyState(context)
        # We need to pass markat_data_manager
        result = await context["logic"](state_obj, market_data_manager)
        
        signal_dict = None
        if isinstance(result, tuple):
            if len(result) >= 3:
                signal_dict = result[2]
        elif isinstance(result, dict):
            signal_dict = result

        return {
            "strategy": context["name"],
            "symbol": context["symbol"],
            "timestamp": datetime.now().isoformat(),
            "signal": signal_dict,
            "raw_result": str(result)[:500] # Truncated for safety
        }
    except Exception as e:
        logger.error(f"Manual tick error for {strategy_id}: {e}")
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
