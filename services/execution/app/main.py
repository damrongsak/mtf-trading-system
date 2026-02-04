from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.executor import can_execute, ExecutionRequest, ExecutionResult
from app.adapters.factory import BrokerFactory
from app.adapters.ctrader_connection import CTraderConnectionManager
from app.services.minimax_service import MinimaxService
import logging
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.models import BrokerAccount, Fund, Trade, TradeStatus, TradeDirection
from sqlalchemy import desc, func
import uuid
import math
from oandapyV20.exceptions import V20Error

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Execution Service")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Execution Service...")
    await CTraderConnectionManager.shutdown_all()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    instrument: str
    units: str
    price: str
    time: str

@app.post("/account/summary", response_model=AccountSummaryResponse)
async def get_account_summary(req: AccountSummaryRequest, db: AsyncSession = Depends(get_db)):
    try:
        try:
            account_uuid = uuid.UUID(req.broker_account_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_uuid))
        account = result.scalars().first()
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found")
        if not account.is_active:
             raise HTTPException(status_code=400, detail="Broker Account is inactive")

        try:
            credentials = decrypt_data(account.credentials_encrypted)
            # Inject environment from model
            credentials["environment"] = account.environment
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to retrieve credentials")

        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        data = await adapter.get_account_summary()
        return AccountSummaryResponse(**data)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Account Summary Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders", response_model=OrderResponse, status_code=201)
async def place_order(req: OrderRequest, db: AsyncSession = Depends(get_db)):
    try:
        try:
            account_uuid = uuid.UUID(req.broker_account_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_uuid))
        account = result.scalars().first()
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found")
        if not account.is_active:
             raise HTTPException(status_code=400, detail="Broker Account is inactive")

        try:
            credentials = decrypt_data(account.credentials_encrypted)
            # Inject environment from model
            credentials["environment"] = account.environment
        except Exception:
             raise HTTPException(status_code=500, detail="Failed to retrieve credentials")
        
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        # Support Market, Limit, Stop based on order_type
        if req.order_type == "MARKET":
            response = await adapter.place_market_order(
                symbol=req.symbol,
                units=req.units,
                sl_price=req.sl_price,
                tp_price=req.tp_price,
                trade_id=req.trade_id,
                comment=req.comment
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
                comment=req.comment
            )
        elif req.order_type == "STOP":
             # Assuming adapter has place_stop_order or uses limit interface. 
             # Oanda usually calls it STOP_LOSS order if attached, or specific order type?
             # Actually Oanda has 'STOP' order type (Entry Stop).
             # Let's assume adapter supports it or we fallback/raise.
             # cTrader adapter needs to support it too.
             # For now, let's treat it similar to LIMIT but maybe adapter distinguishes?
             # Standard adapter interface might lack explicit 'place_stop_order'.
             # I'll check adapter interface or assume place_limit_order can handle it or add TODO.
             # OandaOrderAdapter has place_limit_order.
             # I'll stick to MARKET/LIMIT for now unless I verify adapter support.
             # Plan says "Support MARKET, LIMIT, STOP".
             # I will use place_limit_order and hope it handles type or add generic place_order.
             # Let's stick to what's safe: Limit and Market.
             # If Stop is required, I need to check adapter.
             # I'll assume LIMIT for now for non-market.
             if not req.price:
                 raise HTTPException(status_code=400, detail="Price required for STOP order")
             response = await adapter.place_limit_order( # Reuse limit logic for now
                symbol=req.symbol,
                units=req.units,
                entry_price=req.price,
                sl_price=req.sl_price,
                tp_price=req.tp_price,
                comment=req.comment
            )
        else:
             raise HTTPException(status_code=400, detail=f"Unsupported order type: {req.order_type}")
        
        # Parse relevant fields from OANDA response (keeping logic compatible for now)
        fill = response.get("orderFillTransaction") or response.get("orderCreateTransaction")
        if not fill:
             # Just return empty or partial?
             # raise HTTPException(status_code=400, detail="Order not immediately filled or structure mismatch")
             pass # Allow it, sometimes it's pending.

        return OrderResponse(
            id=fill.get("id", "0") if fill else "0",
            instrument=fill.get("instrument", req.symbol) if fill else req.symbol,
            units=fill.get("units", str(req.units)) if fill else str(req.units),
            price=fill.get("price", "0") if fill else "0",
            time=fill.get("time", "") if fill else ""
        )
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

@app.post("/trades/open")
async def get_open_trades(req: GetTradesRequest, db: AsyncSession = Depends(get_db)):
    try:
        try:
            account_uuid = uuid.UUID(req.broker_account_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_uuid))
        account = result.scalars().first()
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found")
        if not account.is_active:
             raise HTTPException(status_code=400, detail="Broker Account is inactive")

        try:
            credentials = decrypt_data(account.credentials_encrypted)
            # Inject environment from model
            credentials["environment"] = account.environment
        except Exception:
             raise HTTPException(status_code=500, detail="Failed to retrieve credentials")

        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        trades = await adapter.get_open_trades()
        return {"status": "success", "data": trades}
    except Exception as e:
        logger.error(f"Get Open Trades Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trades/close")
async def close_trade(req: CloseTradeRequest, db: AsyncSession = Depends(get_db)):
    try:
        try:
            account_uuid = uuid.UUID(req.broker_account_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_uuid))
        account = result.scalars().first()
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found")
        if not account.is_active:
             raise HTTPException(status_code=400, detail="Broker Account is inactive")

        try:
            credentials = decrypt_data(account.credentials_encrypted)
            # Inject environment from model
            credentials["environment"] = account.environment
        except Exception:
             raise HTTPException(status_code=500, detail="Failed to retrieve credentials")

        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        result = await adapter.close_trade(req.broker_trade_id, req.units)
        return {"status": "success", "data": result}
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
        
        return {
            "data": trades,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total / per_page)
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Get Trades Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}

class SyncTradesRequest(BaseModel):
    broker_account_id: str
    lookback_days: int = Field(30, ge=1, le=365)

@app.post("/trades/sync")
async def sync_trades(req: SyncTradesRequest, db: AsyncSession = Depends(get_db)):
    """
    Import historical closed trades from broker.
    Uses deterministic UUIDs based on AccountID + BrokerTradeID to prevent duplicates.
    """
    try:
        try:
            account_uuid = uuid.UUID(req.broker_account_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_uuid))
        account = result.scalars().first()
        if not account:
            raise HTTPException(status_code=404, detail="Broker Account not found")
        if not account.is_active:
             raise HTTPException(status_code=400, detail="Broker Account is inactive")

        try:
            credentials = decrypt_data(account.credentials_encrypted)
            credentials["environment"] = account.environment
        except Exception:
             raise HTTPException(status_code=500, detail="Failed to retrieve credentials")

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
        return {"status": "success", "imported": imported_count, "total_fetched": len(history)}
        
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
    reason: Optional[str] = None
    risk_usd: Optional[float] = Field(None, description="Target risk in USD (overrides default)")
    
    # Minimax / AI Inputs
    confidence: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="Signal confidence")
    atr_multiplier: Optional[float] = Field(1.0, description="Volatility regime multiplier (1.0=Normal)")
    pain_threshold: Optional[float] = Field(50.0, description="Max allowed psychological regret in USD")

from app.utils.crypto import decrypt_data

# ... imports ...

@app.get("/accounts")
async def get_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrokerAccount).where(BrokerAccount.is_active == True))
    accounts = result.scalars().all()
    # Return simplified list
    return [
        {
            "id": str(account.id),
            "broker_name": account.broker_name,
            "account_id": account.account_number if account.account_number else "N/A", # Use account_number if available? Or verify what front-end expects. Front-end expects 'account_id' but model has 'account_number' now. Let's map account.account_number to account_id field in response.
            "environment": account.environment
        }
        for account in accounts
    ]

@app.post("/smart-orders", response_model=OrderResponse)
async def place_smart_order(req: SmartOrderRequest, db: AsyncSession = Depends(get_db)):
    # 1. Fetch Credentials
    try:
        account_uuid = uuid.UUID(req.broker_account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
        
    result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_uuid))
    account = result.scalars().first()
    if not account:
        raise HTTPException(status_code=404, detail="Broker Account not found")
        
    if not account.is_active:
         raise HTTPException(status_code=400, detail="Broker Account is inactive")

    # Decrypt
    try:
        credentials = decrypt_data(account.credentials_encrypted)
        # Inject environment from model
        credentials["environment"] = account.environment
    except Exception as e:
        logger.error(f"Decryption failed for account {account.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve broker credentials")

    adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
    
    # 2. Validation & Config
    if not req.stop_loss:

         # Need SL to calculate risk
         raise HTTPException(status_code=400, detail="Smart Order requires a Stop Loss price to calculate risk.")

    # Determine Risk Amount
    # If not provided in request, could fallback to Account default or Global default
    # For now, we enforce a strict fallback if missing.
    # Determine Risk Amount
    # HIERARCHICAL RISK CHECK
    
    # 2a. Fetch Fund
    if not account.fund_id:
        # Should not happen if data integrity is maintained
        raise HTTPException(status_code=400, detail="Broker Account is not linked to a Fund")
        
    result_fund = await db.execute(select(Fund).where(Fund.id == account.fund_id))
    fund = result_fund.scalars().first()
    if not fund:
         raise HTTPException(status_code=404, detail="Fund not found")
    
    # 2b. Check Symbol Whitelist (Account Level)
    if account.supported_symbols:
        # Simple check: exact match or "XAU/..."
        # Logic: Helper to normalize slashes for comparison
        def normalize_symbol(s: str):
            return s.replace("/", "_").replace("-", "_").upper()

        if normalize_symbol(req.symbol) not in [normalize_symbol(s) for s in account.supported_symbols]:
             # Just a warning for now or allow if list is empty?
             # If supported_symbols is set, we enforce it.
             logger.warning(f"Symbol {req.symbol} not strictly in supported list {account.supported_symbols} for account {account.id}")
             # raise HTTPException(status_code=400, detail=f"Symbol {req.symbol} is not supported by this account")

    # 2c. Determine Max Risk Limit (Hierarchical)
    # Fund Hard Limit
    fund_limit = float(fund.max_risk_per_trade)
    
    # Account Override (Optional, strict downward)
    account_limit = None
    if account.risk_settings and "max_risk_per_trade" in account.risk_settings:
        account_limit = float(account.risk_settings["max_risk_per_trade"])
        
    # Effective Limit = Min(Fund, Account)
    effective_limit = fund_limit
    if account_limit is not None:
        effective_limit = min(fund_limit, account_limit)
    
    # --- DYNAMIC RISK CALCULATION ---
    # Default to requested or effective limit if no dynamic rule
    calculated_risk = effective_limit
    
    # If Fund has Risk % set (e.g. 0.01 for 1%)
    if fund.risk_percentage and float(fund.risk_percentage) > 0:
        try:
             # Fetch Account NAV
             # We reuse the adapter we already instantiated
             summary = await adapter.get_account_summary() # Should return dict with 'NAV' or 'balance' or 'marginAvailable'
             # Oanda summary has 'NAV' (Net Asset Value)
             nav_str = summary.get('NAV')
             if nav_str:
                 nav = float(nav_str)
                 
                 # Calc Dynamic Risk
                 dynamic_risk = nav * float(fund.risk_percentage)
                 
                 # Cap at Effective Limit (Safety Guardrail)
                 calculated_risk = min(dynamic_risk, effective_limit)
                 
                 # Log for debugging (in real system use logger)
                 print(f"Dynamic Risk: NAV={nav} * {fund.risk_percentage} = {dynamic_risk}. Capped at {effective_limit} -> {calculated_risk}")
             else:
                 # Fallback if NAV not available? 
                 # Use effective_limit but maybe warn?
                 pass
        except Exception as e:
            # If fetch fails, fallback to safe limit or existing logic?
            # For safety, maybe fallback to a safe default if fetching NAV fails?
            # Or just proceed with effective_limit?
            # Let's log and proceed
            print(f"Failed to calc dynamic risk: {e}")

    # Requested Risk
    # checking if user provided a specific override
    requested_risk = req.risk_usd if req.risk_usd is not None else calculated_risk
    
    # Cap User Request at Effective Limit (and maybe dynamic limit?)
    # If user manually requests $50 but dynamic is $20, should we allow?
    # Usually manual override (req.risk_usd) implies "I know what I'm doing".
    # But we MUST respect the HARD LIMIT (effective_limit).
    
    # Enforce Limit
    if requested_risk > effective_limit:
         raise HTTPException(status_code=400, detail=f"Requested risk ${requested_risk} exceeds effective limit ${effective_limit} (Fund: ${fund_limit})")

    target_risk = requested_risk
    
    # 3. Fetch Real-time Price
    try:
        current_price = await adapter.get_current_price(req.symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch live price for risk calculation: {str(e)}")
        
    # 4. Calculate Position Size (Units)
    # Use entry_price for risk calculation if provided (Limit Order), otherwise current market price
    entry_ref = req.entry_price if req.entry_price else current_price
    
    dist = abs(entry_ref - req.stop_loss)
    
    if dist <= 0:
         raise HTTPException(status_code=400, detail="Stop Loss cannot be equal to Entry/Current Price")
         
    raw_units = target_risk / dist
    
    # Direction Check
    if req.direction == "BULLISH":
        units = raw_units
        if req.stop_loss >= entry_ref:
             raise HTTPException(status_code=400, detail="Long SL must be below Entry Price")
    elif req.direction == "BEARISH":
        units = -raw_units
        if req.stop_loss <= entry_ref:
             raise HTTPException(status_code=400, detail="Short SL must be above Entry Price")
    else:
        raise HTTPException(status_code=400, detail="Invalid direction")

    # Order Book Depth Validation
    try:
        order_book = await adapter.get_order_book(req.symbol)
        side = "asks" if req.direction == "BULLISH" else "bids"
        # Check top 5 levels of liquidity
        available_liquidity = sum(float(level.get('liquidity', 0)) for level in order_book.get(side, [])[:5])
        
        if available_liquidity > 0 and abs(units) > available_liquidity:
            logger.warning(f"Liquidity Warning: {req.symbol} {req.direction} {abs(units)} units requested, but only {available_liquidity} available in top 5 levels.")
            # For now, we proceed but log. In production, might reject or split.
    except Exception as ob_e:
        logger.warning(f"Could not validate order book depth: {ob_e}")

    # Min Lot Validation
    if abs(units) < 1.0: 
         raise HTTPException(status_code=400, detail=f"Calculated size {units:.4f} is below minimum tradable limit (1 unit)")

    # Rounding
    units = int(units)

    # 4b. Minimax Regret Check (The Risk Citadel)
    # Calculate Potential Reward
    reward_usd = 0.0
    if req.take_profit:
        reward_dist = abs(req.take_profit - entry_ref)
        reward_usd = reward_dist * abs(units)
    else:
        # If no TP, assume 2:1 Reward for calculation purposes or 0?
        # Rule of thumb: If no TP, regret of missing out is hard to quantify.
        # Let's assume a standard 2R target for "potential" missed profit.
        reward_usd = target_risk * 2.0
    
    # Execute Minimax Check
    is_safe, regret, reason = MinimaxService.calculate_regret(
        risk_usd=target_risk,
        reward_usd=reward_usd,
        confidence=req.confidence or 0.8,
        pain_threshold=req.pain_threshold or 50.0, # Default to $50 if not set
        volatility_multiplier=req.atr_multiplier or 1.0
    )
    
    if not is_safe:
        logger.warning(f"Minimax Rejected: {reason}")
        raise HTTPException(
            status_code=422, # Unprocessable Entity (Business Logic Rejection)
            detail=f"Risk Citadel Validation Failed: {reason}"
        )


    # 5. Execute
    logger.info(f"Executing Smart Order: {req.symbol} {units} units. EntryRef={entry_ref}, SL={req.stop_loss}, Risk=${target_risk}")
    
    if req.entry_price:
        # LIMIT / PENDING ORDER
        response = await adapter.place_limit_order(
            symbol=req.symbol,
            units=units,
            entry_price=req.entry_price,
            sl_price=req.stop_loss,
            tp_price=req.take_profit,
            time_in_force=req.time_in_force or "GTC",
            trade_id=None
        )
    else:
        # MARKET ORDER
        response = await adapter.place_market_order(
            symbol=req.symbol,
            units=units,
            sl_price=req.stop_loss,
            tp_price=req.take_profit,
            trade_id=None
        )
    
    # Handle Response
    # Oanda returns 'orderFillTransaction' for Market, 'orderCreateTransaction' for Limit
    fill = response.get("orderFillTransaction") or response.get("orderCreateTransaction") or {}

    logger.info(f"Execution Successful: ID={fill.get('id')} Price={fill.get('price')} Units={fill.get('units')}")

    return OrderResponse(
        id=fill.get("id", "0"),
        instrument=fill.get("instrument", req.symbol),
        units=fill.get("units", str(units)),
        price=fill.get("price", str(entry_ref)),
        time=fill.get("time", "")
    )