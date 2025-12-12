from fastapi import APIRouter, HTTPException, Body, Depends, status
from sqlalchemy.orm import Session
from app.services.internal_client import execution_client
from app.services.trade_service import TradeService
from app.database import get_db
from app.security import get_current_user
from app.models.user_fund import User
from app.models.trade import Trade, TradeStatus
from app.utils.response import success_response
from app.schemas.trade import TradeResponse
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/execution",
    tags=["execution"]
)

@router.get("/account/summary")
async def get_account_summary():
    try:
        data = await execution_client.get_account_summary()
        return data
    except Exception as e:
        # Improve error handling (e.g. 503 if services down)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders")
async def place_order(
    order_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        logger.info(f"Received order request: {order_data}")
        # 1. Execute Order
        execution_result = await execution_client.place_order(order_data)
        
        # 2. Persist Trade & Create Journal Entry
        if execution_result and "id" in execution_result:
            try:
                TradeService.create_trade_from_execution(
                    db=db,
                    user=current_user,
                    execution_data=execution_result,
                    request_data=order_data
                )
            except Exception as persist_error:
                # Log error but don't fail the request since order was placed
                logger.error(f"Failed to persist trade: {persist_error}", exc_info=True)
                
        return execution_result
    except Exception as e:
        logger.error(f"Error placing order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trades/{trade_id}/close")
async def close_trade(
    trade_id: str,
    payload: Dict[str, float] = Body(..., embed=False), # expect {"exit_price": 123.45}
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually close a trade (MVP) to calculate PnL.
    """
    try:
        exit_price = payload.get("exit_price")
        if exit_price is None:
            raise HTTPException(status_code=400, detail="exit_price is required")
            
        trade = TradeService.close_trade(db, trade_id, exit_price)
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
            
        return {
            "status": "success",
            "trade_id": str(trade.trade_id),
            "pnl": float(trade.pnl_usd),
            "exit_price": float(trade.exit_price)
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades")
async def get_trades(
    status: str = "OPEN",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trades filtered by status.
    """
    try:
        # Convert string status to Enum
        trade_status = TradeStatus[status.upper()]

        # Sync with Oanda if requesting OPEN trades
        if trade_status == TradeStatus.OPEN:
            try:
                oanda_trades = await execution_client.get_open_trades()
                TradeService.sync_open_trades(db, oanda_trades, current_user)
            except Exception as sync_err:
                logger.error(f"Failed to sync Oanda trades: {sync_err}", exc_info=True)
                # Continue to return local DB trades even if sync fails

        trades = db.query(Trade).filter(Trade.status == trade_status).all()
        # Convert SQLAlchemy models to Pydantic models
        trades_response = [TradeResponse.model_validate(t) for t in trades]
        return success_response(data=trades_response)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    except Exception as e:
        logger.error(f"Error fetching trades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
