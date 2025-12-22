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