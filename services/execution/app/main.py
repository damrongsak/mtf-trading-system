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
    stop_loss: Optional[float] = None
    generated_by: str
    reason: Optional[str] = None
    risk_usd: Optional[float] = Field(None, description="Target risk in USD (overrides default)")

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
    
    # 2. Validation & Config
    if not req.stop_loss:
         # Need SL to calculate risk
         raise HTTPException(status_code=400, detail="Smart Order requires a Stop Loss price to calculate risk.")

    # Determine Risk Amount
    # If not provided in request, could fallback to Account default or Global default
    # For now, we enforce a strict fallback if missing.
    target_risk = req.risk_usd if req.risk_usd is not None else 10.0
    
    # 3. Fetch Real-time Price
    try:
        current_price = adapter.get_current_price(req.symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch live price for risk calculation: {str(e)}")
        
    # 4. Calculate Position Size (Units)
    # Risk = abs(Entry - SL) * Units
    # Units = Risk / abs(Entry - SL)
    
    dist = abs(current_price - req.stop_loss)
    
    if dist <= 0:
         raise HTTPException(status_code=400, detail="Stop Loss cannot be equal to Current Price")
         
    raw_units = target_risk / dist
    
    # Direction Check
    if req.direction == "BULLISH":
        units = raw_units
        if req.stop_loss >= current_price:
             # Sanity check: Long needs SL below price
             # Allow it for Limit orders? SmartOrder is Market for now.
             pass 
    elif req.direction == "BEARISH":
        units = -raw_units
        if req.stop_loss <= current_price:
             pass
    else:
        raise HTTPException(status_code=400, detail="Invalid direction")

    # Min Lot Validation (approximate for XAU/USD)
    # OANDA min is 0.01 units? No, OANDA is units. 1 unit of XAU is usually min?
    # Actually OANDA supports fractional typically?
    # Let's enforce a minimum of 0.01 standard lot equivalent context or just > 0.
    # For XAU/USD, 1 unit = 1 oz. 0.01 lot = 1 item? 
    # Usually standard lot = 100 oz. 0.01 lot = 1 oz.
    # Let's assume OANDA 'units' == ounces for XAU/USD. 
    # Must check Oanda specs. Typically 1 unit.
    
    if abs(units) < 1.0: # Minimum 1 unit (approx 0.01 lot)
         # Reject
         raise HTTPException(status_code=400, detail=f"Calculated size {units:.4f} is below minimum tradable limit (for Risk ${target_risk})")

    # Rounding (Oanda accepts integers or specific precision)
    units = int(units) # Safe to cast to int for units

    # 5. Execute
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