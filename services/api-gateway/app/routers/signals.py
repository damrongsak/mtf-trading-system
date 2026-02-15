from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Optional, Any, List
from app.routers.execution import success_response
from app.schemas.response import APIResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.signal_log import SignalLog
from app.models.deployment import Deployment
from app.security import get_current_user
from app.models.user import User
from app.services.internal_client import execution_client
from app.services.trade_service import TradeService
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/signals",
    tags=["signals"]
)

@router.post("/{signal_id}/approve")
async def approve_signal(
    signal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually approve a PENDING_APPROVAL signal for execution.
    """
    signal = db.query(SignalLog).filter(SignalLog.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
        
    if signal.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=400, detail=f"Signal is not pending approval (status: {signal.status})")

    # 1. Fetch Deployment Context
    deployment = db.query(Deployment).filter(Deployment.id == signal.deployment_id).first()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment linked to signal not found")

    # Verify ownership
    if deployment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to approve this signal")

    try:
        # 2. Prepare Execution Payload
        # We reuse the logic from internal.py but with manual approval context
        broker_account_id = deployment.config_snapshot.get("broker_account_id")
        if not broker_account_id:
             raise HTTPException(status_code=400, detail="Broker Account ID not found in deployment config")

        smart_order_payload = {
            "broker_account_id": str(broker_account_id),
            "symbol": signal.symbol,
            "direction": signal.direction,
            "stop_loss": signal.meta_data.get("stop_loss") if signal.meta_data else None,
            "risk_usd": signal.meta_data.get("risk_usd") if signal.meta_data else deployment.config_snapshot.get("risk_usd", 10.0),
            "generated_by": f"HITL-{deployment.id.hex[:8]}",
            "reason": f"Manual Approval: {signal.reason}"
        }

        # 3. Call Execution Service
        result = await execution_client.place_smart_order(smart_order_payload)
        
        # 4. Snapshot Result & Persist Trade
        if result and "id" in result:
             try:
                trade = TradeService.create_trade_from_execution(
                    db=db,
                    user=current_user,
                    execution_data=result,
                    request_data=smart_order_payload
                )
                trade.broker_account_id = broker_account_id
                trade.deployment_id = deployment.id
                
                # Update Metadata
                meta = trade.metadata_json or {}
                meta["deployment_id"] = str(deployment.id)
                meta["approved_by"] = str(current_user.id)
                trade.metadata_json = meta
                
                # Update Signal Status
                signal.status = "EXECUTED"
                signal.execution_id = result.get("id")
                
                # Update Deployment Last Signal
                deployment.last_signal_at = trade.signal_timestamp
                
                db.commit()
             except Exception as pe:
                 logger.error(f"Failed to persist approved trade: {pe}")
                 # We committed signal status change if possible, or rollback?
                 # If order was placed, we should at least mark signal as EXECUTED.
                 signal.status = "EXECUTED"
                 db.commit()

        return {"status": "success", "data": result}

    except Exception as e:
        logger.error(f"Approval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{signal_id}/reject")
async def reject_signal(
    signal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject a PENDING_APPROVAL signal.
    """
    signal = db.query(SignalLog).filter(SignalLog.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
        
    if signal.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=400, detail=f"Signal is not pending approval (status: {signal.status})")

    # Verify ownership via Deployment
    deployment = db.query(Deployment).filter(Deployment.id == signal.deployment_id).first()
    if deployment and deployment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to reject this signal")

    signal.status = "REJECTED"
    db.commit()
    
    return {"status": "success", "message": "Signal rejected"}

@router.post("/cancel-all", response_model=APIResponse[Dict[str, int]])
async def cancel_all_pending_signals(
    deployment_id: Optional[str] = None,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Reject all signals that are in PENDING_APPROVAL state.
    Optional filters: deployment_id, symbol.
    """
    query = db.query(SignalLog).filter(SignalLog.status == "PENDING_APPROVAL")
    
    if deployment_id:
        try:
            dep_uuid = UUID(deployment_id)
            query = query.filter(SignalLog.deployment_id == dep_uuid)
        except ValueError:
             raise HTTPException(status_code=400, detail="Invalid deployment_id")
             
    if symbol:
        query = query.filter(SignalLog.symbol == symbol.upper())
        
    signals = query.all()
    count = 0
    for s in signals:
        s.status = "REJECTED"
        s.meta_data = {**(s.meta_data or {}), "rejection_reason": "Bulk Cancel"}
    db.commit()
    return success_response(data={"cancelled": count})
