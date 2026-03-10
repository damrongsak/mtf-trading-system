from fastapi import FastAPI, HTTPException, Depends, Body, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.utils.response import success_response, error_response
from app.schemas.response import APIResponse
from app.executor import can_execute, ExecutionRequest, ExecutionResult
from app.adapters.factory import BrokerFactory
from app.adapters.ctrader_connection import CTraderConnectionManager
from app.services.minimax_service import MinimaxService
import logging
import asyncio
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.models import BrokerAccount, Fund, Trade, TradeStatus, TradeDirection
from app.utils.crypto import decrypt_data
from sqlalchemy import desc, func
import uuid
import math
from oandapyV20.exceptions import V20Error
from app.services.order_service import OrderService
from app.services.cache_service import execution_cache
from app.worker import worker, fill_trade_consumer
from app.health import verify_dependencies
from app.core.scheduler import scheduler
from app.services.equity_guardian import EquityGuardian
from app.services.janitor_service import JanitorService
from app.services.oanda_streamer import MultiStreamManager
from app.core.config import settings
import redis.asyncio as redis
from fastapi.security import APIKeyHeader

# Security
API_KEY_NAME = "X-Internal-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_internal_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Could not validate credentials for internal service access",
        )
    return api_key

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Execution Service")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Execution Service...")
    
    # Verify critical dependencies before accepting traffic
    await verify_dependencies()
    
    # Start background workers
    asyncio.create_task(worker.start())

    # [HFT-Lite] Start FillTradeConsumer: reads execution.filled.stream → persists Trade to DB
    # This keeps the execution hot path DB-free.
    asyncio.create_task(fill_trade_consumer.start())

    # Initialize Equity Guardian
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        guardian = EquityGuardian(redis_client)
        
        # Schedule Health Check
        scheduler.add_job(guardian.check_health, 'interval', minutes=5, misfire_grace_time=60)
        
        # [THE JANITOR] Schedule State Reconciliation every 1 minute
        scheduler.add_job(JanitorService.reconcile_all_accounts, 'interval', minutes=1, misfire_grace_time=60)
        
        # [STREAMER] Schedule Stream Sync every 5 minutes (to handle new/deleted accounts)
        scheduler.add_job(MultiStreamManager.sync_streams, 'interval', minutes=5, misfire_grace_time=60)
        
        # Initial stream sync
        asyncio.create_task(MultiStreamManager.sync_streams())
        
        scheduler.start()
        logger.info("✅ Equity Guardian & Scheduler Started")
        
        # Start Trade Consumer (Optional: if we want real-time updates)
        # For now, let's rely on the scheduled hydration or add a listener if needed.
        # The original implementation had a TradeEventConsumer. 
        # We can add a simple redis pubsub listener here if needed, but for now strict polling + hydration is safer for migration.
        
    except Exception as e:
        logger.error(f"❌ Equity Guardian Init Failed: {e}")
    
    # [HFT-lite] Pre-hydrate L3 Execution Cache for all active accounts
    # This eliminates the cold-start latency (DB I/O) on the first live trade command.
    # It runs in a background task so it does not block service readiness.
    asyncio.create_task(_warmup_execution_cache())

async def _warmup_execution_cache():
    """
    [HFT-lite] Deep Warm-up of the Execution Cache.
    Pre-populates Redis and L1 (memory) with:
    1. Active Broker Accounts & Credentials
    2. Associated Funds
    3. Mandatory Risk Filters
    4. cTrader Symbol/Contract ID mappings
    """
    try:
        from app.database import AsyncSessionLocal
        from app.models import BrokerAccount, Fund, RiskFilter, TargetType
        from sqlalchemy import select, or_
        from app.adapters.factory import BrokerFactory
        from app.utils.crypto import decrypt_data
        from app.services.cache_service import execution_cache
        import uuid
        
        async with AsyncSessionLocal() as db:
            # 1. Fetch all active accounts
            result = await db.execute(select(BrokerAccount).where(BrokerAccount.is_active == True))
            accounts = result.scalars().all()
            
            if not accounts:
                logger.info("[HFT-lite] No active accounts found for cache warm-up.")
                return

            logger.info(f"[HFT-lite] Warming up cache for {len(accounts)} active accounts...")
            
            warmed_funds = set()
            ctrader_hydrated = False

            for account in accounts:
                acc_id = str(account.id)
                # Cache Account
                await execution_cache.set_account(acc_id, {
                    "id": acc_id,
                    "is_active": account.is_active,
                    "broker_name": account.broker_name,
                    "credentials_encrypted": account.credentials_encrypted,
                    "environment": account.environment,
                    "fund_id": str(account.fund_id) if account.fund_id else None,
                    "risk_settings": account.risk_settings,
                    "account_number": account.account_number
                })
                
                # Cache Credentials (L1 only)
                try:
                    creds = decrypt_data(account.credentials_encrypted)
                    creds["environment"] = account.environment
                    execution_cache.set_credentials(acc_id, creds)
                except Exception as ce:
                    logger.warning(f"[HFT-lite] Failed to decrypt credentials for {account.broker_name}:{acc_id}: {ce}")
                    continue

                # Cache Fund
                if account.fund_id and str(account.fund_id) not in warmed_funds:
                    fund_res = await db.execute(select(Fund).where(Fund.id == account.fund_id))
                    fund = fund_res.scalars().first()
                    if fund:
                        fund_id = str(fund.id)
                        await execution_cache.set_fund(fund_id, {
                            "id": fund_id,
                            "max_risk_per_trade": float(fund.max_risk_per_trade),
                            "risk_percentage": float(fund.risk_percentage) if fund.risk_percentage else 0
                        })
                        
                        # Cache Risk Filters for this Fund
                        conditions = [
                            RiskFilter.target_type == TargetType.SYSTEM.value,
                            RiskFilter.target_type == TargetType.FUND.value,
                            RiskFilter.target_id == fund.id
                        ]
                        filter_res = await db.execute(
                            select(RiskFilter).where(RiskFilter.is_enabled == True).where(or_(*conditions))
                        )
                        filters = filter_res.scalars().all()
                        filters_raw = [
                            {"filter_type": f.filter_type, "config_json": f.threshold_parameters, "is_enabled": f.is_enabled} 
                            for f in filters
                        ]
                        await execution_cache.set_risk_filters(fund_id, filters_raw)
                        warmed_funds.add(fund_id)

                # Special: cTrader Symbol Cache (once per provider)
                if account.broker_name == "CTRADER" and not ctrader_hydrated:
                    try:
                        adapter = BrokerFactory.get_adapter("CTRADER", creds)
                        await adapter._populate_symbol_cache()
                        ctrader_hydrated = True
                    except Exception as e:
                        logger.warning(f"[HFT-lite] cTrader symbol hydration failed: {e}")

        logger.info(f"[HFT-lite] ✅ Execution Cache deep warm-up complete.")
    except Exception as e:
        logger.error(f"[HFT-lite] ❌ Execution Cache warm-up failed: {e}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Execution Service...")
    await worker.stop()
    await fill_trade_consumer.stop()
    scheduler.stop()
    await CTraderConnectionManager.shutdown_all()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(ConnectionResetError)
async def connection_reset_handler(request, exc):
    logger.error(f"Global ConnectionResetError caught: {exc}")
    return error_response(message="Internal Connection Reset by Peer. Please retry.", code=503)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    if isinstance(exc, HTTPException):
        raise exc
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return error_response(message=f"Internal Server Error: {str(exc)}", code=500)


# --- Request Models ---

class BrokerConfig(BaseModel):
    broker_name: str = Field(..., example="OANDA")
    credentials: Dict[str, Any] = Field(..., description="API Key, Account ID, etc.")

class AccountSummaryRequest(BaseModel):
    broker_account_id: str

class OrderRequest(BaseModel):
    broker_account_id: str
    symbol: str = Field(..., description="Instrument e.g., XAU_USD")
    order_type: str = Field("MARKET", description="MARKET, LIMIT, STOP")
    units: float = Field(..., description="Units to trade (positive=long, negative=short)")
    price: Optional[float] = None # For Limit/Stop
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    trade_id: Optional[str] = None
    comment: Optional[str] = None
    tag: Optional[str] = None

class GetTradesRequest(BaseModel):
    broker_account_id: str

class CloseTradeRequest(BaseModel):
    broker_account_id: str
    broker_trade_id: str
    units: Optional[float] = None

# ...

class AccountSummaryResponse(BaseModel):
    balance: str
    NAV: str
    marginAvailable: str
    openTradeCount: int
    openPositionCount: int

class OrderResponse(BaseModel):
    id: str
    instrument: Optional[str] = None
    units: Optional[str] = None
    price: Optional[str] = None
    time: Optional[str] = None
    status: str = Field("PENDING", description="PENDING, FILLED, CANCELLED, REJECTED")

async def get_account_and_credentials(account_id_str: str, db: AsyncSession):
    """Helper to resolve account and credentials with caching."""
    try:
        account_uuid = uuid.UUID(account_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    # 1. Try Cache
    account_data = await execution_cache.get_account(account_id_str)
    credentials = await execution_cache.get_credentials(account_id_str)

    if account_data and credentials:
        # Mock account object for compatibility
        account = type('obj', (object,), account_data)
        return account, credentials

    # 2. Fallback to DB
    result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_uuid))
    account = result.scalars().first()
    if not account:
        raise HTTPException(status_code=404, detail="Broker Account not found")
    
    if not account.is_active:
        raise HTTPException(status_code=400, detail="Broker Account is inactive")

    # Decrypt and Cache
    try:
        if not credentials:
# Credentials resolved from cache or decrypted
            credentials = decrypt_data(account.credentials_encrypted)
            credentials["environment"] = account.environment
            execution_cache.set_credentials(account_id_str, credentials)
        
        if not account_data:
            account_data = {
                "id": str(account.id),
                "is_active": account.is_active,
                "broker_name": account.broker_name,
                "credentials_encrypted": account.credentials_encrypted,
                "environment": account.environment,
                "fund_id": str(account.fund_id) if account.fund_id else None,
                "risk_settings": account.risk_settings,
                "account_number": account.account_number
            }
            await execution_cache.set_account(account_id_str, account_data)
            account = type('obj', (object,), account_data)

        return account, credentials
    except Exception as e:
        logger.error(f"Failed to resolve credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve broker credentials")

@app.post("/account/summary", response_model=APIResponse[AccountSummaryResponse])
async def get_account_summary(authenticated: str = Depends(verify_internal_api_key), req: AccountSummaryRequest = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        account, credentials = await get_account_and_credentials(req.broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        data = await adapter.get_account_summary()
        return success_response(data=data)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Account Summary Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders", response_model=APIResponse[OrderResponse], status_code=201)
async def place_order(authenticated: str = Depends(verify_internal_api_key), req: OrderRequest = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        account, credentials = await get_account_and_credentials(req.broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        # [Latency] HFT-Lite: If cTrader, try to warm up connection
        if account.broker_name == "CTRADER":
            await adapter.client.connect()

        # Support Market, Limit, Stop based on order_type
        if req.order_type == "MARKET":
            response = await adapter.place_market_order(
                symbol=req.symbol,
                units=req.units,
                sl_price=req.sl_price,
                tp_price=req.tp_price,
                trade_id=req.trade_id,
                comment=req.comment,
                tag=req.tag
            )
        elif req.order_type == "LIMIT":
            if not req.price:
                 raise HTTPException(status_code=400, detail="Price required for LIMIT order")
            response = await adapter.place_limit_order(
                symbol=req.symbol,
                units=req.units,
                entry_price=req.price,
                sl_price=req.sl_price,
                tp_price=req.tp_price,
                comment=req.comment,
                tag=req.tag
            )
        elif req.order_type == "STOP":
             if not req.price:
                 raise HTTPException(status_code=400, detail="Price required for STOP order")
             response = await adapter.place_limit_order( # Reuse limit logic for now
                symbol=req.symbol,
                units=req.units,
                entry_price=req.price,
                sl_price=req.sl_price,
                tp_price=req.tp_price,
                comment=req.comment,
                tag=req.tag
            )
        else:
             raise HTTPException(status_code=400, detail=f"Unsupported order type: {req.order_type}")
        
        # Parse relevant fields from OANDA response
        trade_id = "0"
        fill = response.get("orderFillTransaction")
        if fill:
             # For Market Orders, use the resulting Trade ID for subsequent operations
             trade_id = fill.get("tradeOpened", {}).get("tradeID", fill.get("id", "0"))
        else:
             fill = response.get("orderCreateTransaction")
             trade_id = fill.get("id", "0") if fill else "0"

        return success_response(data={
            "id": trade_id,
            "instrument": fill.get("instrument", req.symbol) if fill else req.symbol,
            "units": fill.get("units", str(req.units)) if fill else str(req.units),
            "price": fill.get("price", "0") if fill else "0",
            "time": fill.get("time", "") if fill else "",
            "status": "FILLED" if fill and fill.get("price") else "PENDING"
        })
    except HTTPException as he:
        raise he
    except V20Error as ve:
        logger.error(f"OANDA API Error: {ve}")
        raise HTTPException(status_code=400, detail=f"OANDA Error: {str(ve)}")
    except ValueError as ve:
        logger.error(f"Value Error: {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid Input: {str(ve)}")
    except Exception as e:
        logger.error(f"Place Order Error: {e}", exc_info=True)
        # Expose error detail for debugging (in dev/test envs this is acceptable)
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")


@app.get("/orders", response_model=APIResponse[List[OrderResponse]])
async def get_pending_orders_list(
    authenticated: str = Depends(verify_internal_api_key),
    broker_account_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        account, credentials = await get_account_and_credentials(broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        try:
            orders = await adapter.get_pending_orders()
            # Map to OrderResponse
            mapped = []
            for o in orders:
                mapped.append(OrderResponse(
                    id=str(o.get('id')),
                    instrument=o.get('instrument'),
                    units=str(o.get('units')),
                    price=str(o.get('price')),
                    time=str(o.get('time')),
                    status=o.get('status', 'PENDING')
                ))
            return success_response(data=mapped)
        except NotImplementedError:
            # Fallback for brokers that don't support pending orders
            logger.info(f"Broker {account.broker_name} does not support pending orders.")
            return success_response(data=[])
        except Exception as e:
            logger.error(f"Error fetching pending orders: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Get Pending Orders Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class CancelOrderRequest(BaseModel):
    broker_account_id: str
    order_id: Optional[str] = None # Optional if cancelling all

@app.delete("/orders")
async def cancel_pending_orders(
    authenticated: str = Depends(verify_internal_api_key),
    broker_account_id: str = None, 
    symbol: Optional[str] = None, 
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel ALL pending orders for an account.
    Optional filter by symbol.
    """
    try:
        account, credentials = await get_account_and_credentials(broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        # 1. Fetch Pending Orders
        # We need a get_pending_orders method on adapter? 
        # Or OANDA adapter has get_orders?
        # Let's assume adapter has get_pending_orders or we use get_open_orders generic?
        # Standardize check:
        if not hasattr(adapter, 'get_pending_orders'):
             # OANDA specific fallback?
             # For now, implemented loosely. Oanda adapter needs get_pending_orders.
             # If not implemented, we can't do bulk safely without fetching first.
             raise HTTPException(status_code=501, detail="Broker adapter does not support bulk cancellation (missing get_pending_orders)")
        
        orders = await adapter.get_pending_orders()
        cancelled_count = 0
        errors = []
        
        for o in orders:
            # Filter by symbol
            if symbol and o.get('instrument') != symbol:
                continue
            
            oid = o.get('id')
            if oid:
                try:
                    await adapter.cancel_order(oid)
                    cancelled_count += 1
                except Exception as ce:
                    errors.append(f"Failed to cancel {oid}: {str(ce)}")

        return success_response(data={"cancelled": cancelled_count, "errors": errors})

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Bulk Cancel Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trades/open")
async def get_open_trades(req: GetTradesRequest, db: AsyncSession = Depends(get_db), authenticated: str = Depends(verify_internal_api_key)):
    try:
        account, credentials = await get_account_and_credentials(req.broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        trades = await adapter.get_open_trades()
        return success_response(data=trades)
    except Exception as e:
        logger.error(f"Get Open Trades Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trades/close")
async def close_trade(authenticated: str = Depends(verify_internal_api_key), req: CloseTradeRequest = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        account, credentials = await get_account_and_credentials(req.broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        result = await adapter.close_trade(req.broker_trade_id, req.units)
        return success_response(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trades")
async def get_trades(
    broker_account_id: Optional[str] = None,
    status: Optional[TradeStatus] = None,
    symbol: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical trades with filtering and pagination.
    """
    try:
        query = select(Trade)
        
        # Filters
        if broker_account_id:
            try:
                acc_uuid = uuid.UUID(broker_account_id)
                query = query.where(Trade.broker_account_id == acc_uuid)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid UUID format for broker_account_id")
        
        if status:
            query = query.where(Trade.status == status)
            
        if symbol:
            query = query.where(Trade.symbol == symbol)
            
        # Count Total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()
        
        # Pagination & Ordering
        query = query.order_by(desc(Trade.signal_timestamp))
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await db.execute(query)
        trades = result.scalars().all()
        
        return success_response(
            data=trades,
            meta={
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": math.ceil(total / per_page)
            }
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Get Trades Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return success_response(data={"status": "ok"})

class SyncTradesRequest(BaseModel):
    broker_account_id: str
    lookback_days: int = Field(30, ge=1, le=365)

@app.post("/trades/sync")
async def sync_trades(authenticated: str = Depends(verify_internal_api_key), req: SyncTradesRequest = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Import historical closed trades from broker.
    Uses deterministic UUIDs based on AccountID + BrokerTradeID to prevent duplicates.
    """
    try:
        account, credentials = await get_account_and_credentials(req.broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        # Calculate Range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=req.lookback_days)
        
        logger.info(f"Syncing trades for {account.id} from {start_date} to {end_date}")

        # Fetch History
        history = await adapter.get_trade_history(start_date, end_date)
        logger.info(f"Fetched {len(history)} trades from adapter")
        
        imported_count = 0
        
        for t_data in history:
            ext_id = str(t_data.get("trade_id"))
            if not ext_id: continue
            
            # If trade_id is missing from the adapter response, generate a deterministic one
            # This is a fallback for adapters that might not provide a unique trade_id for historical trades
            if not t_data.get("trade_id"):
                t_data["trade_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{t_data['signal_timestamp']}-{t_data['symbol']}-{t_data.get('entry_price')}"))
            
            # Generate Deterministic ID
            trade_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{str(account.id)}_{ext_id}")
            
            # Upsert using merge
            new_trade = Trade(
                trade_id=trade_uuid,
                broker_account_id=account.id,
                symbol=t_data["symbol"],
                strategy_name=t_data.get("strategy_name", "Imported"),
                signal_timestamp=t_data["signal_timestamp"],
                status=t_data["status"],
                direction=t_data["direction"],
                entry_price=t_data["entry_price"],
                exit_price=t_data["exit_price"],
                sl_price=t_data.get("sl_price", 0),
                tp_price=t_data.get("tp_price", 0),
                lot_size=t_data["lot_size"],
                risk_usd=t_data["risk_usd"],
                pnl_usd=t_data["pnl_usd"],
                exit_timestamp=t_data["exit_timestamp"],
                metadata_json=t_data.get("metadata_json", {"external_id": ext_id})
            )
            await db.merge(new_trade)
            imported_count += 1
        
        await db.commit()
        return success_response(
            data={"imported": imported_count, "total_fetched": len(history)},
            message=f"Imported {imported_count} trades"
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Sync Trades Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Smart Execution ---

class SmartOrderRequest(BaseModel):
    broker_account_id: str
    symbol: str
    direction: str # BULLISH / BEARISH
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_price: Optional[float] = None
    time_in_force: Optional[str] = "GTC"
    slippage_tolerance: Optional[float] = None
    generated_by: str
    signal_id: Optional[str] = None # For traceability
    reason: Optional[str] = None
    risk_usd: Optional[float] = Field(None, description="Target risk in USD (overrides default)")
    
    # Minimax / AI Inputs
    confidence: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="Signal confidence")
    atr_multiplier: Optional[float] = Field(1.0, description="Volatility regime multiplier (1.0=Normal)")
    pain_threshold: Optional[float] = Field(50.0, description="Max allowed psychological regret in USD")

# Security utils

@app.get("/accounts")
async def get_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrokerAccount).where(BrokerAccount.is_active == True))
    accounts = result.scalars().all()
    data = [
        {
            "id": str(account.id),
            "broker_name": account.broker_name,
            "account_id": account.account_number if account.account_number else "N/A",
            "environment": account.environment
        }
        for account in accounts
    ]
    return success_response(data=data)

@app.post("/smart-orders", response_model=APIResponse[OrderResponse])
async def place_smart_order(authenticated: str = Depends(verify_internal_api_key), req: SmartOrderRequest = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        req_data = req.dict()
        result = await OrderService.execute_smart_order(req_data, db)
        return success_response(data=result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Smart Order Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Order Management ---

class CancelOrderRequest(BaseModel):
    broker_account_id: str
    order_id: str

class AmendOrderRequest(BaseModel):
    broker_account_id: str
    units: Optional[float] = None
    price: Optional[float] = None
    stop_loss: Optional[float] = Field(None, alias="sl_price")
    take_profit: Optional[float] = Field(None, alias="tp_price")
    trailing_stop: Optional[bool] = Field(None, alias="trailing_sl")

    model_config = {
        "populate_by_name": True
    }

class AmendPositionRequest(BaseModel):
    broker_account_id: str
    stop_loss: Optional[float] = Field(None, alias="sl_price")
    take_profit: Optional[float] = Field(None, alias="tp_price")
    trailing_stop: Optional[bool] = Field(None, alias="trailing_sl")

    model_config = {
        "populate_by_name": True
    }

@app.delete("/orders/{order_id}")
async def cancel_order(order_id: str, broker_account_id: str, db: AsyncSession = Depends(get_db), authenticated: str = Depends(verify_internal_api_key)):
    try:
        account, credentials = await get_account_and_credentials(broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        if hasattr(adapter, 'cancel_order'):
            res = await adapter.cancel_order(order_id)
            return success_response(data=res)
        else:
            raise HTTPException(status_code=501, detail="Broker adapter does not support cancellation")

    except ValueError as ve:
        logger.warning(f"Order not found for cancellation: {order_id}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Cancel Order Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/orders/{order_id}")
async def amend_order(authenticated: str = Depends(verify_internal_api_key), order_id: str = Path(...), req: AmendOrderRequest = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        account, credentials = await get_account_and_credentials(req.broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        if hasattr(adapter, 'amend_order'):
            res = await adapter.amend_order(
                order_id=order_id,
                units=req.units,
                price=req.price,
                sl_price=req.stop_loss,
                tp_price=req.take_profit,
                trailing_sl=req.trailing_stop
            )
            
            # Sync to local DB if trade exists
            try:
                acc_uuid = uuid.UUID(req.broker_account_id)
                stmt = select(Trade).where(
                    Trade.broker_trade_id == str(order_id),
                    Trade.broker_account_id == acc_uuid
                )
                result = await db.execute(stmt)
                trade = result.scalar_one_or_none()
                if trade:
                    if req.stop_loss is not None: trade.sl_price = req.stop_loss
                    if req.take_profit is not None: trade.tp_price = req.take_profit
                    if req.trailing_stop is not None: trade.trailing_stop = req.trailing_stop
                    await db.commit()
            except Exception as db_err:
                logger.error(f"Failed to sync order amendment to DB: {db_err}")

            return success_response(data=res)
        else:
            raise HTTPException(status_code=501, detail="Broker adapter does not support order amendment")

    except ValueError as ve:
        logger.warning(f"Order not found for amendment: {order_id}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        # [SAFETY] Check if this is a Risk Validation error (422) from the adapter
        from app.adapters.ctrader import RiskValidationError
        if isinstance(e, RiskValidationError):
            logger.warning(f"[SAFETY] Pre-trade risk check failed for amend order {order_id}: {e}")
            raise HTTPException(status_code=422, detail=f"Risk validation failed: {str(e)}")
        logger.error(f"Amend Order Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/positions/{position_id}")
async def amend_position(authenticated: str = Depends(verify_internal_api_key), position_id: str = Path(...), req: AmendPositionRequest = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        account, credentials = await get_account_and_credentials(req.broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        if hasattr(adapter, 'amend_position'):
            res = await adapter.amend_position(
                broker_trade_id=position_id,
                sl_price=req.stop_loss,
                tp_price=req.take_profit,
                trailing_sl=req.trailing_stop
            )
            
            # Sync to local DB if trade exists
            try:
                acc_uuid = uuid.UUID(req.broker_account_id)
                stmt = select(Trade).where(
                    Trade.broker_trade_id == str(position_id),
                    Trade.broker_account_id == acc_uuid
                )
                result = await db.execute(stmt)
                trade = result.scalar_one_or_none()
                if trade:
                    if req.stop_loss is not None: trade.sl_price = req.stop_loss
                    if req.take_profit is not None: trade.tp_price = req.take_profit
                    if req.trailing_stop is not None: trade.trailing_stop = req.trailing_stop
                    await db.commit()
            except Exception as db_err:
                logger.error(f"Failed to sync position amendment to DB: {db_err}")
                
            return success_response(data=res)
        else:
            raise HTTPException(status_code=501, detail="Broker adapter does not support position amendment")

    except ValueError as ve:
        logger.warning(f"Position not found for amendment: {position_id}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Amend Position Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class CloseAllTradesRequest(BaseModel):
    broker_account_id: str
    symbol: Optional[str] = None

@app.post("/trades/close-all")
async def close_all_trades(req: CloseAllTradesRequest, db: AsyncSession = Depends(get_db), authenticated: str = Depends(verify_internal_api_key)):
    try:
        account, credentials = await get_account_and_credentials(req.broker_account_id, db)
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        open_trades = await adapter.get_open_trades()
        closed_count = 0
        errors = []
        
        for t in open_trades:
            # Filter by symbol if requested
            if req.symbol and t.get('instrument') != req.symbol:
                continue
                
            try:
                # OANDA/CTrader trade ID
                tid = t.get('id')
                if tid:
                    await adapter.close_trade(tid)
                    closed_count += 1
            except Exception as ce:
                errors.append(str(ce))
                
        return success_response(data={"closed_count": closed_count, "errors": errors})

    except Exception as e:
        logger.error(f"Close All Trades Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))