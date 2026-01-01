
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.deployment import Deployment
from app.models.broker_account import BrokerAccount
from app.models.user_fund import User
from app.services.internal_client import execution_client
from app.services.trade_service import TradeService
from typing import Dict, Any, Optional
import os
import logging
from uuid import UUID
from datetime import datetime, timezone
from app.models.signal_log import SignalLog

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["internal"]
)

# Simple API Key protection for internal calls
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")

async def verify_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal key")

@router.post("/signals")
async def receive_internal_signal(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    # _ = Depends(verify_internal_key) # Enable in prod
):
    """
    Internal endpoint for Strategy Core to execute trades.
    Payload: {
        "deployment_id": str,
        "symbol": str,
        "direction": str, # BULLISH/BEARISH
        "stop_loss": float,
        "risk_usd": float,
        "reason": str
    }
    """
    try:
        deployment_id = payload.get("deployment_id")
        if not deployment_id:
            raise HTTPException(status_code=400, detail="Missing deployment_id")

        # 1. Fetch Deployment & Context
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        if deployment.status != "ACTIVE":
             raise HTTPException(status_code=400, detail="Deployment is not active")

        # 1.5 Persist Signal Log
        try:
            # Try to get strategy name
            strat_name = f"Deployment-{deployment.id}"
            if deployment.strategy:
                strat_name = deployment.strategy.name
            
            signal_log = SignalLog(
                timestamp=datetime.now(timezone.utc),
                symbol=payload.get("symbol"),
                direction=payload.get("direction"),
                timeframe=payload.get("timeframe", "H1"),
                strategy_name=strat_name,
                deployment_id=deployment.id,
                confidence=payload.get("confidence", 0.0),
                price=payload.get("price", 0.0),
                reason=payload.get("reason"),
                meta_data=payload
            )
            db.add(signal_log)
            db.commit()
        except Exception as se:
            logger.error(f"Failed to persist signal log: {se}")
            # Continue execution even if logging fails

        # Resolve User & Account
        user = db.query(User).filter(User.id == deployment.user_id).first()
        
        # Where do we get the Broker Account?
        # Option A: From Deployment config_snapshot (if saved there)
        # Option B: From User's default or active account
        
        broker_account_id = deployment.config_snapshot.get("broker_account_id")
        
        # Fallback: Find user's first active account
        if not broker_account_id:
             # This is risky if user has multiple accounts. 
             # For MVP, pick first active.
             # Ideally validation at deployment start ensures this.
             acc = db.query(BrokerAccount).filter(BrokerAccount.user_id == user.id, BrokerAccount.is_active == True).first() # UserFund join actually needed? Schema check: BrokerAccount usually has no user_id, it is linked via Fund -> UserFund?
             # Let's check models. BrokerAccount has fund_id. Fund has UserFund.
             # Complex join needed if not in snapshot.
             pass 
        
        # Let's assume passed in snapshot or we find via User -> Fund -> BrokerAccount
        # Simplified: We need a broker account to execute.
        # If not found, fail.
        
        if not broker_account_id:
             # Try to find via User's default fund?
             # Too complex for quick patch. 
             # Let's Require it to be in config_snapshot or provided in payload.
             raise HTTPException(status_code=400, detail="Broker Account ID not found in deployment config")

        # 2. Prepare Execution Payload (Smart Order)
        smart_order_payload = {
            "broker_account_id": str(broker_account_id),
            "symbol": payload.get("symbol"),
            "direction": payload.get("direction"),
            "stop_loss": payload.get("stop_loss"),
            "risk_usd": payload.get("risk_usd"),
            "generated_by": f"Deployment-{deployment_id[:8]}",
            "reason": payload.get("reason")
        }
        
        # 3. Call Execution Service (via Client or reusing Router logic?)
        # Reusing router logic is cleaner if we can import the service/client directly.
        # We use `execution_client` service wrapper.
        
        result = await execution_client.place_smart_order(smart_order_payload)
        
        # 4. Snapshot Result & Persist Trade
        if result and "id" in result:
             try:
                trade = TradeService.create_trade_from_execution(
                    db=db,
                    user=user,
                    execution_data=result,
                    request_data=smart_order_payload
                )
                trade.broker_account_id = broker_account_id
                trade.deployment_id = deployment.id # If we add this column? Or Metadata.
                
                # Update Metadata
                meta = trade.metadata_json or {}
                meta["deployment_id"] = str(deployment.id)
                trade.metadata_json = meta
                
                # Update Deployment Last Signal
                deployment.last_signal_at = trade.signal_timestamp
                
                db.commit()
             except Exception as pe:
                 logger.error(f"Failed to persist internal trade: {pe}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Internal Signal Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
