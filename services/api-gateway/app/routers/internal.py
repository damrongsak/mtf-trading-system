
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.deployment import Deployment
from app.models.broker_account import BrokerAccount
from app.models.user import User
from app.services.internal_client import execution_client
from app.services.trade_service import TradeService
from typing import Dict, Any, Optional
import os
import logging
from uuid import UUID
from datetime import datetime, timezone
from app.models.signal_log import SignalLog
from app.routers.telegram import send_telegram_message
from app.models.telegram_chat_mapping import TelegramChatMapping
from app.models.strategy_execution_log import StrategyExecutionLog
from app.models.market import MarketSymbol

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
        "deployment_id": Optional[str],
        "strategy_id": Optional[str],
        "symbol": str,
        "direction": str, # BULLISH/BEARISH
        "stop_loss": float,
        "take_profit": Optional[float],
        "risk_usd": float,
        "reason": str,
        "timeframe": Optional[str]
    }
    """
    try:
        deployment_id = payload.get("deployment_id")
        strategy_id = payload.get("strategy_id")
        
        if not deployment_id and not strategy_id:
            raise HTTPException(status_code=400, detail="Missing deployment_id or strategy_id")

        deployment = None
        strategy = None
        user_ids = []
        strat_name = "Unknown Strategy"
        execution_mode = "SEMI_AUTO"  # Default: Human in the Loop (phase 1)
        broker_account_id = None

        # 1. Resolve Context (Deployment vs Template Strategy)
        if deployment_id:
            deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
            if not deployment:
                raise HTTPException(status_code=404, detail="Deployment not found")
            if deployment.status != "ACTIVE":
                raise HTTPException(status_code=400, detail="Deployment is not active")
            
            user_ids = [deployment.user_id]
            strat_name = deployment.strategy.name if deployment.strategy else f"Deployment-{deployment_id[:8]}"
            execution_mode = deployment.config_snapshot.get("execution_mode", "AUTO")
            broker_account_id = deployment.config_snapshot.get("broker_account_id")
        else:
            from app.models.strategy import Strategy
            from app.models.user_fund import UserFund
            strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            # Fetch owners/managers of the fund associated with the strategy
            fund_users = db.query(UserFund).filter(UserFund.fund_id == strategy.fund_id).all()
            user_ids = [fu.user_id for fu in fund_users]
            
            strat_name = strategy.name
            # HITL ENFORCEMENT: Template strategies are ALWAYS SEMI_AUTO (Human in the Loop).
            # config_json AUTO is ignored - only MANUAL is allowed as alternative.
            # Only Deployments (with explicit config_snapshot) can be truly AUTO.
            cfg_mode = strategy.config_json.get("execution_mode", "SEMI_AUTO")
            execution_mode = "SEMI_AUTO" if cfg_mode == "AUTO" else cfg_mode
            broker_account_id = strategy.broker_account_id

        # 1.2 Check for Existing Active Signals (Throttling)
        filter_args = [
            SignalLog.symbol == payload.get("symbol"),
            SignalLog.status.in_(["PENDING_APPROVAL", "PLACED", "OPEN"]),
            SignalLog.direction == payload.get("direction")
        ]
        if deployment_id:
            filter_args.append(SignalLog.deployment_id == deployment.id)
        else:
            filter_args.append(SignalLog.strategy_id == strategy.id)

        active_signal = db.query(SignalLog).filter(*filter_args).order_by(SignalLog.timestamp.desc()).first()

        if active_signal:
            logger.info(f"Signal throttled: Active signal {active_signal.id} exists.")
            return {"status": "ignored", "reason": "Active signal exists", "signal_id": str(active_signal.id)}

        # 1.5 Persist Signal Log
        signal_log = SignalLog(
            timestamp=datetime.now(timezone.utc),
            symbol=payload.get("symbol"),
            direction=payload.get("direction"),
            timeframe=payload.get("timeframe", "H1"),
            strategy_name=strat_name,
            deployment_id=deployment.id if deployment else None,
            strategy_id=strategy.id if strategy else None,
            confidence=payload.get("confidence", 0.0),
            price=payload.get("price", 0.0),
            reason=payload.get("reason"),
            meta_data=payload
        )
        db.add(signal_log)
        db.commit()

        # 1.6 Telegram Notifications (To all relevant users)
        try:
            for u_id in user_ids:
                mapping = db.query(TelegramChatMapping).filter(
                    TelegramChatMapping.user_id == u_id,
                    TelegramChatMapping.is_active == True
                ).first()
                if mapping:
                    msg = (
                        f"🔔 **New Signal: {strat_name}**\n\n"
                        f"**Symbol**: `{payload.get('symbol')}`\n"
                        f"**Direction**: {payload.get('direction')}\n"
                        f"**Price**: {payload.get('price', 'N/A')}\n"
                        f"**Reason**: {payload.get('reason')}\n"
                    )
                    if execution_mode in ("SEMI_AUTO", "MANUAL"):
                        msg += f"\n⚠️ *รอการอนุมัติ (Human Review)*\n[Dashboard](http://localhost/signals)"
                    else:
                        msg += f"\n⚡ *Executing {execution_mode}*"
                    
                    await send_telegram_message(mapping.chat_id, msg)
        except Exception as te:
            logger.error(f"Failed to send Telegram notifications: {te}")

        # 1.7 Check Execution Flow
        if execution_mode == "SEMI_AUTO" or execution_mode == "MANUAL":
            signal_log.status = "PENDING_APPROVAL"
            db.commit()
            return {"status": "pending_approval", "signal_id": str(signal_log.id)}

        # 2. Prepare Execution Payload (Smart Order)
        if not broker_account_id:
            raise HTTPException(status_code=400, detail="Broker Account ID not found")

        smart_order_payload = {
            "broker_account_id": str(broker_account_id),
            "symbol": payload.get("symbol"),
            "direction": payload.get("direction"),
            "stop_loss": payload.get("stop_loss"),
            "take_profit": payload.get("take_profit"),
            "risk_usd": payload.get("risk_usd"),
            "generated_by": f"{'Dep' if deployment_id else 'Strat'}-{ (deployment_id or strategy_id)[:8] }",
            "reason": payload.get("reason"),
            "client_order_id": str(signal_log.id)
        }
        
        # 3. Call Execution Service
        try:
            result = await execution_client.place_smart_order(smart_order_payload)
        except Exception as exec_err:
            # Execution service might be temporarily unavailable.
            # Signal is already persisted + Telegram sent. Return gracefully.
            logger.error(f"Execution service call failed: {exec_err}")
            signal_log.status = "EXECUTION_FAILED"
            db.commit()
            return {"status": "logged_pending_exec", "signal_id": str(signal_log.id), "error": "Execution service unavailable"}
        
        # 4. Snapshot Result & Update Log
        if result and "id" in result:
             try:
                # Find User for Trade Service (picking first in case of multiple, though usually 1 owner)
                user = db.query(User).filter(User.id == user_ids[0]).first() if user_ids else None
                
                trade = TradeService.create_trade_from_execution(
                    db=db,
                    user=user,
                    execution_data=result,
                    request_data=smart_order_payload
                )
                trade.broker_account_id = broker_account_id
                if deployment:
                    trade.deployment_id = deployment.id
                
                # Update Metadata
                meta = trade.metadata_json or {}
                if deployment: meta["deployment_id"] = str(deployment.id)
                if strategy: meta["strategy_id"] = str(strategy.id)
                trade.metadata_json = meta
                
                # Update Last Signal
                if deployment: deployment.last_signal_at = trade.signal_timestamp
                
                signal_log.status = "PLACED"
                signal_log.execution_id = result.get("id")
                
                db.commit()
             except Exception as pe:
                 logger.error(f"Failed to persist trade/update status: {pe}")

        return result

    except HTTPException:
        raise
@router.post("/strategy-logs")
async def receive_strategy_logs(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Internal endpoint to receive essential strategy logs.
    """
    deployment_id = payload.get("deployment_id")
    output = payload.get("output")
    
    if not deployment_id or not output:
        return {"status": "ignored"}

    try:
        log = StrategyExecutionLog(
            deployment_id=deployment_id,
            essential_output=output
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to persist strategy log: {e}")
        
    return {"status": "success"}

@router.patch("/symbols/{symbol}/details")
async def update_symbol_details(
    symbol: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    # _ = Depends(verify_internal_key) # Enable in prod
):
    """
    Internal endpoint to update symbol details (e.g. calibrated EFP params).
    """
    ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == symbol).first()
    if not ms:
        # Try cleaning
        alt_symbol = symbol.replace("_", "/").replace("-", "/")
        ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == alt_symbol).first()
        
    if not ms:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

    # Merge details (using a copy to ensure SQLAlchemy detects the change)
    current_details = (ms.details or {}).copy()
    current_details.update(payload)
    ms.details = current_details
    
    db.commit()
    return {"status": "success", "symbol": symbol, "details": ms.details}
