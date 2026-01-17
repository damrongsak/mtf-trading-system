
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.signal_log import SignalLog
from app.schemas import ExecutionMode
from app.adapters.execution import execution_client
from app.config_cache import config_cache
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals")

@router.post("/{signal_id}/approve")
async def approve_signal(signal_id: str, db: Session = Depends(get_db)):
    """
    Manually approve a PENDING_APPROVAL signal for execution.
    """
    signal = db.query(SignalLog).filter(SignalLog.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
        
    if signal.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=400, detail=f"Signal is not pending approval (status: {signal.status})")
        
    try:
        # 1. Reconstruct Context
        # strategy_name format: "Strategy-{id}"
        if not signal.strategy_name.startswith("Strategy-"):
            raise HTTPException(status_code=400, detail="Invalid strategy mapping")
            
        strategy_id = signal.strategy_name.replace("Strategy-", "")
        
        # 2. Construct Payload
        # We rely on what's in signal log and config cache
        # If config is gone from cache, we might have an issue. 
        # But for active strategies, it should be there.
        # Minimal payload reconstruction:
        
        order_payload = {
            # "broker_account_id": ... we need this. 
            # It's not in SignalLog. We might need to fetch strategy config again.
            "symbol": signal.symbol,
            "direction": signal.direction,
            "stop_loss": None, # Retrieving specific SL from meta_data if available
            "generated_by": strategy_id,
            "reason": f"Manual Approval of {signal.reason}"
        }
        
        # Try to get SL from metadata
        if signal.meta_data and "stop_loss" in signal.meta_data:
            order_payload["stop_loss"] = float(signal.meta_data["stop_loss"])
            
        # Get Broker Account ID from Config Cache or DB strategy
        config = config_cache.get_config(strategy_id)
        if config:
            order_payload["broker_account_id"] = str(config.get("broker_account_id", ""))
        else:
             # Fallback? Or fail? Execution Service might need it.
             # If Deployment ID was valid, we could look that up.
             # For MVP, warning.
             logger.warning(f"Config not found for {strategy_id}, sending without account ID (Execution might fail)")
        
        # 3. Execute
        response = await execution_client.place_order(order_payload)
        
        # 4. Update Status
        signal.status = "EXECUTED"
        signal.execution_id = response.get("id") if isinstance(response, dict) else str(response)
        db.commit()
        
        return {"status": "executed", "execution_response": response}
        
    except Exception as e:
        logger.error(f"Approval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{signal_id}/reject")
async def reject_signal(signal_id: str, db: Session = Depends(get_db)):
    """
    Reject a PENDING_APPROVAL signal.
    """
    signal = db.query(SignalLog).filter(SignalLog.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
        
    if signal.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=400, detail=f"Signal is not pending approval (status: {signal.status})")
        
    signal.status = "REJECTED"
    db.commit()
    
    return {"status": "rejected"}
