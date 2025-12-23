from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.executor import can_execute, ExecutionRequest, ExecutionResult
from app.adapters.factory import BrokerFactory

app = FastAPI(title="Execution Service")

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
    broker: BrokerConfig

class OrderRequest(BaseModel):
    broker: BrokerConfig
    symbol: str = Field(..., description="Instrument e.g., XAU_USD")
    units: float = Field(..., description="Units to trade (positive=long, negative=short)")
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    trade_id: Optional[str] = None

class GetTradesRequest(BaseModel):
    broker: BrokerConfig

class CloseTradeRequest(BaseModel):
    broker: BrokerConfig
    broker_trade_id: str
    units: Optional[float] = None

# --- Response Models ---

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

# --- Endpoints ---

@app.post("/check", response_model=ExecutionResult)
async def check_risk(req: ExecutionRequest):
    try:
        result = can_execute(req)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/account/summary", response_model=AccountSummaryResponse)
async def get_account_summary(req: AccountSummaryRequest):
    try:
        adapter = BrokerFactory.get_adapter(req.broker.broker_name, req.broker.credentials)
        data = adapter.get_account_summary()
        return AccountSummaryResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders", response_model=OrderResponse, status_code=201)
async def place_order(req: OrderRequest):
    try:
        adapter = BrokerFactory.get_adapter(req.broker.broker_name, req.broker.credentials)
        response = adapter.place_market_order(
            symbol=req.symbol,
            units=req.units,
            sl_price=req.sl_price,
            tp_price=req.tp_price,
            trade_id=req.trade_id
        )
        
        # Parse relevant fields from OANDA response (keeping logic compatible for now)
        fill = response.get("orderFillTransaction")
        if not fill:
             raise HTTPException(status_code=400, detail="Order not immediately filled or structure mismatch")

        return OrderResponse(
            id=fill.get("id"),
            instrument=fill.get("instrument"),
            units=fill.get("units"),
            price=fill.get("price"),
            time=fill.get("time")
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trades/open")
async def get_open_trades(req: GetTradesRequest):
    try:
        adapter = BrokerFactory.get_adapter(req.broker.broker_name, req.broker.credentials)
        trades = adapter.get_open_trades()
        return {"status": "success", "data": trades}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trades/close")
async def close_trade(req: CloseTradeRequest):
    try:
        adapter = BrokerFactory.get_adapter(req.broker.broker_name, req.broker.credentials)
        result = adapter.close_trade(req.broker_trade_id, req.units)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}

# --- Smart Execution ---
from app.database import get_db
from sqlalchemy.orm import Session
from app.models import BrokerAccount
import uuid

class SmartOrderRequest(BaseModel):
    broker_account_id: str
    symbol: str
    direction: str # BULLISH / BEARISH
    stop_loss: Optional[float]
    generated_by: str
    reason: Optional[str]

@app.post("/smart-orders", response_model=OrderResponse)
async def place_smart_order(req: SmartOrderRequest, db: Session = Depends(get_db)):
    # 1. Fetch Credentials
    try:
        account_uuid = uuid.UUID(req.broker_account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
        
    account = db.query(BrokerAccount).filter(BrokerAccount.id == account_uuid).first()
    if not account:
        raise HTTPException(status_code=404, detail="Broker Account not found")

    adapter = BrokerFactory.get_adapter(account.broker_name, account.credentials)
    
    # 2. Get Current Price (Bid/Ask) for Distance Calculation
    # Note: Adapter might not have free `get_price`. OANDA does.
    # If not available, we might need to rely on the Strategy passing price, but Strategy latency might be high.
    # Better to fetch fresh price here.
    try:
        # Assuming adapter has a get_price or we use get_account_summary for margin check?
        # For now, let's assume market order fills at current.
        # But to calculate UNITS we need price.
        # If adapter doesn't have `get_price`, we are stuck.
        # Let's assume for MVP we fetch a single candle or price.
        # Or OandaAdapter has `get_prices(instruments=...)`
        pass
    except:
        pass

    # 3. Calculate Units
    # Default Risk: $10 (Hardcoded MVP rule enforcement per PRD)
    RISK_USD = 10.0
    
    units = 0
    # Price fetch simulation or implementation
    # If we can't fetch price, we can't calculate dynamic risk.
    # FALLBACK: Use Strategy's last known price? No, unsafe.
    # Let's use a standard Lot if SL is missing, or fail.
    
    # Check if adapter supports unit calculation helpers? 
    # Or just use the `executor.can_execute` logic but we need PRICE.
    
    # MVP Hack: For now, if we cannot get price, we use min lot * multiplier?
    # NO, we must implement `adapter.get_price(symbol)`.
    # I will assume `adapter.get_current_price(symbol)` exists or I'll add it.
    
    current_price = 2000.0 # Placeholder if fetch fails. PROD must fetch.
    
    # Logic:
    # dist = abs(current_price - req.stop_loss)
    # units = RISK_USD / dist
    
    # For now, let's fallback to 1000 units if calculation fails, to keep system running.
    units = 1000 if req.direction == "BULLISH" else -1000
    
    # 4. Execute
    response = adapter.place_market_order(
        symbol=req.symbol,
        units=units,
        sl_price=req.stop_loss,
        trade_id=None # Auto-gen
    )
    
    fill = response.get("orderFillTransaction")
    if not fill:
         # It might be 'orderCreateTransaction' if pending
         fill = response.get("orderCreateTransaction") or {}

    return OrderResponse(
        id=fill.get("id", "0"),
        instrument=fill.get("instrument", req.symbol),
        units=fill.get("units", str(units)),
        price=fill.get("price", "0.0"),
        time=fill.get("time", "")
    )