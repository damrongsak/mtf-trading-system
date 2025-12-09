from fastapi import APIRouter, HTTPException, Body, Depends, status
from sqlalchemy.orm import Session
from app.services.internal_client import execution_client
from app.services.trade_service import TradeService
from app.database import get_db
from app.security import get_current_user
from app.models.user_fund import User
from typing import Dict, Any

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
                print(f"Failed to persist trade: {persist_error}")
                
        return execution_result
    except Exception as e:
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
