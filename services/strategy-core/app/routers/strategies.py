from fastapi import APIRouter, HTTPException, Path
from app.registry import StrategyRegistry
from app.fleet import FleetManager
from app.market_data import market_data_manager
import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Strategies"])

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
async def reload_strategies_endpoint():
    """
    Triggers a hot reload of all strategy plugins.
    Use this after adding or modifying strategy files.
    """
    try:
        logger.info("Executing Strategy Fleet Hot Reload...")
        import asyncio
        loop = asyncio.get_running_loop()
        
        # 1. Reload Physical Templates (Thread-safe)
        await loop.run_in_executor(None, StrategyRegistry.reload_strategies)
        
        # 2. Sync Fleet with Database (Async)
        from app.fleet import FleetManager
        await FleetManager.get_instance().load_fleet()
        
        logger.info("Strategy Fleet Hot Reload completed successfully.")
        return {"status": "success", "message": "Strategies and Fleet reloaded successfully"}
    except Exception as e:
        logger.error(f"Failed to reload strategies: {e}")
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }

@router.post("/{strategy_id}/tick")
async def trigger_manual_tick(strategy_id: str = Path(..., description="ID of the active strategy or deployment")):
    """
    Manually triggers a logic tick for an active strategy or deployment instance.
    """
    fleet = FleetManager.get_instance()
    
    # Institutional FIX: Always reload fleet before manual tick to capture DB patches/fixes
    await fleet.load_fleet()
    
    # 1. Check if it's a legacy Template strategy
    context = fleet.active_strategies.get(strategy_id)
    if context:
        try:
            class StrategyState:
                def __init__(self, ctx):
                    self.config_json = ctx["config"]
                    self.symbol = ctx["symbol"]
                    self.id = ctx["id"]
                    self.fund_id = ctx.get("fund_id")
                    self.broker_account_id = ctx["broker_account_id"]
                    self.timeframe = ctx["config"].get("tf_trigger", "15min")
            
            state_obj = StrategyState(context)
            result = await context["logic"](state_obj, market_data_manager)
            
            signal_dict = None
            reason = "No setup found"
            
            if isinstance(result, tuple):
                if len(result) >= 3:
                    signal_dict = result[2]
            elif isinstance(result, dict):
                signal_dict = result
                
            if signal_dict and "reason" in signal_dict:
                reason = signal_dict["reason"]
            elif isinstance(result, dict) and "message" in result:
                reason = result["message"]

            # Record to observability ring buffer
            fleet.add_strategy_log(
                strategy_id=strategy_id,
                message=reason,
                level="INFO",
                meta={"type": "MANUAL_TICK", "signal": signal_dict}
            )

            return {
                "status": "success",
                "strategy": context["name"],
                "type": "TEMPLATE",
                "symbol": context["symbol"],
                "timestamp": datetime.datetime.now().isoformat(),
                "reason": reason,
                "signal": signal_dict
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Manual tick error for template {strategy_id}: {e}")
            return {"status": "error", "message": str(e)}

    # 2. Check if it's a Dynamic Deployment
    context = fleet.active_deployments.get(strategy_id)
    if context:
        try:
            class DeploymentState:
                def __init__(self, ctx):
                    self.config_json = ctx["config"]
                    self.symbol = ctx["symbol"]
                    self.id = ctx["id"]
            
            state_obj = DeploymentState(context)
            result = await context["executor"].execute(state_obj, market_data_manager)
            
            # Record to observability ring buffer
            fleet.add_strategy_log(
                strategy_id=strategy_id,
                message=result.get("reason", "Dynamic Manual Tick"),
                level="INFO",
                meta={"type": "DYNAMIC_MANUAL_TICK", "signal": result.get("signal")}
            )

            return {
                "status": "success",
                "strategy": context["name"],
                "type": "DYNAMIC",
                "symbol": context["symbol"],
                "timestamp": datetime.datetime.now().isoformat(),
                "reason": result.get("reason", "No dynamic signal generated"),
                "signal": result.get("signal")
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Manual tick error for deployment {strategy_id}: {e}")
            return {"status": "error", "message": str(e)}

    raise HTTPException(status_code=404, detail=f"Active strategy/deployment {strategy_id} not found in fleet.")

@router.get("/{strategy_id}/logs")
async def get_strategy_logs(
    strategy_id: str = Path(..., description="ID of the strategy or deployment"),
    limit: int = 50
):
    """Retrieves recent calculation logs for a strategy."""
    fleet = FleetManager.get_instance()
    logs = fleet.get_strategy_logs(strategy_id, limit=limit)
    return {"status": "success", "strategy_id": strategy_id, "logs": logs}
