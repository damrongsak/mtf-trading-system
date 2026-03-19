from fastapi import APIRouter, HTTPException, Body, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.services.internal_client import execution_client
from app.services.trade_service import TradeService
from app.database import get_db
from app.security import get_current_user
from app.models.user_fund import Fund, UserFund
from app.models.user import User
from app.models.trade import Trade, TradeStatus
from app.models.broker_account import BrokerAccount
from app.utils.crypto import decrypt_data
from app.utils.response import success_response, paginated_response
from app.schemas.trade import TradeResponse
from typing import Dict, Any, List
from datetime import datetime
import logging
import asyncio
import traceback
import uuid
from app.utils.symbol_utils import normalize_symbol

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/execution",
    tags=["execution"]
)

@router.get("/traces/stream")
async def stream_execution_traces(current_user: User = Depends(get_current_user)):
    """
    Server-Sent Events (SSE) stream for real-time execution latency traces.
    Useful for the Dashboard Live Latency Widget.
    """
    async def event_generator():
        from app.utils.redis_client import get_redis_client
        rc = await get_redis_client()
        pubsub = rc.pubsub()
        await pubsub.subscribe("execution:traces")
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_msg=True, timeout=1.0)
                if message:
                    data = message['data']
                    yield f"data: {data}\n\n"
                await asyncio.sleep(0.01) # Small sleep to prevent CPU spinning
        except asyncio.CancelledError:
            await pubsub.unsubscribe("execution:traces")
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/account/summary")
async def get_account_summary(
    account_id: str = None, # Optional: if not provided, might fail or pick default
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Default to first active account if not specified (for MVP)
        query = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            UserFund.user_id == current_user.id,
            BrokerAccount.is_active == True
        )
        if account_id:
            query = query.filter(BrokerAccount.id == account_id)
            
        account = query.first()
        if not account:
            raise HTTPException(status_code=404, detail="No active broker account found")

        data = await execution_client.get_account_summary(str(account.id)) # Pass ID string
        return success_response(data=data)
    except HTTPException:
        raise
    except Exception as e:
        # Improve error handling (e.g. 503 if services down)
        logger.error(f"Error fetching account summary: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/accounts/{account_id}/summary")
async def get_account_summary_by_id(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Spec-aligned path for account summary"""
    return await get_account_summary(account_id=account_id, db=db, current_user=current_user)

@router.post("/accounts/{account_id}/sync")
async def sync_account_trades(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Spec-aligned path to sync trades from broker"""
    try:
        # Verify access
        account = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            BrokerAccount.id == account_id,
            UserFund.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found or access denied")
            
        # Fetch from broker
        broker_trades = await execution_client.get_open_trades(str(account.id))
        
        # Sync to DB
        synced = TradeService.sync_open_trades(
            db=db,
            broker_trades=broker_trades,
            user=current_user,
            broker_account_id=account.id
        )
        
        return success_response(data={"count": len(synced)}, message="Sync completed successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing trades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

from app.schemas.execution import OrderRequest

@router.post("/orders")
async def place_order(
    order_req: OrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Convert Pydantic to Dict for internal processing
        order_data = order_req.model_dump(exclude_none=True)
        logger.info(f"Received order request: {order_data}")
        
        # Resolve Broker Account
        account_id = order_data.get("account_id")
        # Support broker_account_id as alias if frontend uses that
        if not account_id:
             account_id = order_data.get("broker_account_id")

        query = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            UserFund.user_id == current_user.id,
            BrokerAccount.is_active == True
        )
        if account_id:
            query = query.filter(BrokerAccount.id == account_id)
        
        account = query.first()
        if not account:
            raise HTTPException(status_code=404, detail="Broker account not found")

        # 1. Normalize order data for Execution Service (HFT-Lite)
        # Ensure 'price' is used instead of 'limit_price' for LIMIT/STOP orders
        # Ensure 'sl_price' and 'tp_price' are used instead of 'stop_loss' and 'take_profit'
        if "limit_price" in order_data and "price" not in order_data:
            order_data["price"] = order_data.pop("limit_price")
        
        if "stop_loss" in order_data and "sl_price" not in order_data:
            order_data["sl_price"] = order_data.pop("stop_loss")
            
        if "take_profit" in order_data and "tp_price" not in order_data:
            order_data["tp_price"] = order_data.pop("take_profit")

        # 2. Execute Order
        # Pass ID directly
        execution_result = await execution_client.place_order(order_data, str(account.id))
        
        # 3. Persistence: Handled by Execution Service background worker (HFT-Lite)
        # Placeholder trade creation removed to prevent 0-price/mis-scaled records.
                
        return success_response(data=execution_result, message="Order placed successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders")
async def get_pending_orders(
    broker_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Verify access
        account = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            BrokerAccount.id == broker_account_id,
            UserFund.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found or access denied")
            
        data = await execution_client.get_pending_orders(str(account.id))
        return success_response(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pending orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    broker_account_id: str, # Required to know where to cancel
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Verify access
        account = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            BrokerAccount.id == broker_account_id,
            UserFund.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found or access denied")
            
        result = await execution_client.cancel_order(order_id, str(account.id))
        return success_response(data=result, message="Order cancelled successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trades/close-all")
async def close_all_trades(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Emergency endpoint to close ALL open positions for a broker account.
    Optional symbol filter.
    """
    try:
        broker_account_id = payload.get("broker_account_id")
        symbol = normalize_symbol(payload.get("symbol")) if payload.get("symbol") else None
        
        if not broker_account_id:
            raise HTTPException(status_code=400, detail="broker_account_id is required")
            
        # Verify access
        account = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            BrokerAccount.id == broker_account_id,
            UserFund.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found or access denied")
            
        result = await execution_client.close_all_trades(str(account.id), symbol)
        return success_response(data=result, message="Close All command sent successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing all trades: {e}", exc_info=True)
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
    Now integrates with Execution Service to close on Broker.
    """
    try:
        exit_price = payload.get("exit_price")
        
        # 1. Resolve Trade (Dual Search: Internal UUID or Broker ID)
        trade = None
        try:
            # Try UUID first
            trade_uuid = uuid.UUID(trade_id)
            trade = db.query(Trade).filter(Trade.trade_id == trade_uuid).first()
        except (ValueError, TypeError):
            # Not a UUID, try searching by broker_trade_id
            trade = db.query(Trade).filter(Trade.broker_trade_id == trade_id).first()
            
        if not trade:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found in database")
            
        # 2. Close on Broker
        if trade.broker_account_id:
            account = db.query(BrokerAccount).filter(BrokerAccount.id == trade.broker_account_id).first()
            if account:
                # Verify permission for this account
                has_access = db.query(UserFund).join(Fund).filter(
                    UserFund.user_id == current_user.id,
                    Fund.id == account.fund_id
                ).first()
                
                if has_access:
                    oanda_id = trade.metadata_json.get("oanda_id") if trade.metadata_json else None
                    
                    if oanda_id:
                        try:
                            await execution_client.close_trade(
                                trade_id=oanda_id, 
                                broker_account_id=str(account.id)
                            )
                        except Exception as e:
                            logger.error(f"Failed to close trade on broker: {e}")
                            # Could choose to fail here or proceed to close locally
                            # For now, let's proceed but warn.
        
        # 2. Close Locally
        # Use the resolved trade's internal UUID for consistency in TradeService
        trade = TradeService.close_trade(db, str(trade.trade_id), exit_price or 0.0)
            
        return success_response(data={
            "trade_id": str(trade.trade_id),
            "pnl": float(trade.pnl_usd or 0),
            "exit_price": float(trade.exit_price or 0)
        }, message="Trade closed successfully")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trades/open")
async def get_open_trades(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Detect if user is trying to OPEN a trade via this endpoint (common confusion)
        if any(key in payload for key in ["symbol", "units", "direction", "side", "order_type"]):
             raise HTTPException(
                 status_code=400, 
                 detail="This endpoint is for LISTING open trades. To OPEN a new trade, use POST /api/v1/execution/orders"
             )

        broker_account_id = payload.get("broker_account_id")
        if not broker_account_id:
             raise HTTPException(status_code=400, detail="broker_account_id is required")

        # Verify access
        account = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            BrokerAccount.id == broker_account_id,
            UserFund.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found or access denied")

        trades = await execution_client.get_open_trades(str(account.id))
        return success_response(data=trades)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching open trades: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades/open")
async def get_open_trades_get(
    broker_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Spec-aligned GET path for open trades"""
    return await get_open_trades(payload={"broker_account_id": broker_account_id}, db=db, current_user=current_user)

# Alias for /api/v1/execution/trades/open (spec uses plural but frontend might use /positions)
@router.get("/positions")
async def get_open_positions_alias(
    broker_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_open_trades(payload={"broker_account_id": broker_account_id}, db=db, current_user=current_user)

@router.get("/trades")
async def get_trades(
    status: str = "OPEN",
    page: int = 1,
    per_page: int = 20,
    symbol: str = None,
    from_date: str = None,
    to_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trades filtered by status, symbol, and date range.
    """
    # Filter trades by user's funds (via BrokerAccount)
    query = db.query(Trade).join(BrokerAccount).join(Fund).join(UserFund).filter(
        UserFund.user_id == current_user.id
    )

    # Status Filter
    if status != "ALL":
        try:
            trade_status = TradeStatus[status.upper()]
            query = query.filter(Trade.status == trade_status)
            
            # Sync with Oanda if requesting OPEN trades
            if trade_status == TradeStatus.OPEN:
                # Iterate all active accounts for this user
                accounts = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
                    UserFund.user_id == current_user.id, 
                    BrokerAccount.is_active == True
                ).all()
                    
                async def sync_account(acc):
                    if acc.broker_name not in ["OANDA", "CTRADER"]:
                        return # Janitor service handles others
                    try:
                        trades = await execution_client.get_open_trades(str(acc.id))
                        TradeService.sync_open_trades(db, trades, current_user, broker_account_id=acc.id)
                    except Exception as sync_err:
                        logger.error(f"Failed to sync trades for account {acc.account_name}: {sync_err}", exc_info=True)

                if accounts:
                    await asyncio.gather(*[sync_account(acc) for acc in accounts])
                            
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Additional Filters
    if symbol:
        symbol = normalize_symbol(symbol)
        query = query.filter(Trade.symbol.ilike(f"%{symbol}%"))
    
    if from_date:
        query = query.filter(Trade.signal_timestamp >= from_date)
        
    if to_date:
        query = query.filter(Trade.signal_timestamp <= to_date)

    # Pagination logic
    total = query.count()
    trades = query.order_by(Trade.signal_timestamp.desc())\
                  .offset((page - 1) * per_page)\
                  .limit(per_page)\
                  .all()

    trades_response = [TradeResponse.model_validate(t) for t in trades]
    
    meta = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page
    }
    
    # Manually construct paginated response structure if helper not available or to match generic Response
    # Manually construct paginated response structure if helper not available or to match generic Response
    return paginated_response(
        data=trades_response,
        page=page,
        per_page=per_page,
        total=total,
        message="Trades retrieved successfully"
    )

@router.get("/accounts")
async def get_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all broker accounts for the current user.
    """
    try:
        accounts = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            UserFund.user_id == current_user.id,
            BrokerAccount.is_active == True
        ).all()
        
        return success_response(data=[
            {
                "id": str(account.id),
                "broker_name": account.broker_name,
                "account_id": account.account_number,
                "environment": account.environment,
                "is_live": account.is_live,
                "fund_id": str(account.fund_id)
            }
            for account in accounts
        ])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/smart-orders")
async def place_smart_order(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # We could valid user ownership of broker_account_id here, but Execution Service also checks.
        # However, checking here is better for security (Tenant isolation).
        
        account_id = payload.get("broker_account_id")
        if not account_id:
            raise HTTPException(status_code=400, detail="broker_account_id is required")
             
        # Verify ownership (via Fund)
        account = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            BrokerAccount.id == account_id,
            UserFund.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found or access denied")
            
        # Proxy to Execution Service
        result = await execution_client.place_smart_order(payload)
        
        # 3. Persistence: Handled by Execution Service background worker (HFT-Lite)
                 
        return success_response(data=result, message="Smart order placed successfully")
        
    except HTTPException as he:
        raise he
    except Exception as e:
        # Check if it's an HTTP error from the execution client
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
             status_code = e.response.status_code
             try:
                 detail = e.response.json().get("detail", str(e))
             except:
                 detail = str(e)
             logger.error(f"Execution Service Error ({status_code}): {detail}")
             raise HTTPException(status_code=status_code, detail=detail)
             
        logger.error(f"Smart Order Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/orders/{order_id}")
async def amend_order(
    order_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        broker_account_id = payload.get("broker_account_id")
        if not broker_account_id:
            raise HTTPException(status_code=400, detail="broker_account_id is required")
            
        # Verify access
        account = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            BrokerAccount.id == broker_account_id,
            UserFund.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found or access denied")
            
        result = await execution_client.amend_order(order_id, payload)
        return success_response(data=result, message="Order amendment command sent")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error amending order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/positions/{position_id}")
async def amend_position(
    position_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        broker_account_id = payload.get("broker_account_id")
        if not broker_account_id:
            raise HTTPException(status_code=400, detail="broker_account_id is required")
            
        # Verify access
        account = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
            BrokerAccount.id == broker_account_id,
            UserFund.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found or access denied")
            
        # Resolve broker_trade_id from position_id (which might be an internal UUID)
        broker_trade_id = position_id
        try:
            trade_uuid = uuid.UUID(position_id)
            trade = db.query(Trade).filter(Trade.trade_id == trade_uuid).first()
            if trade and trade.broker_trade_id:
                broker_trade_id = trade.broker_trade_id
        except (ValueError, TypeError):
            pass

        result = await execution_client.amend_position(broker_trade_id, payload)
        return success_response(data=result, message="Position amendment command sent")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error amending position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trades/{trade_id}/amend")
async def amend_trade_spec(
    trade_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Spec-aligned path for position amendment"""
    return await amend_position(position_id=trade_id, payload=payload, db=db, current_user=current_user)
