from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from app.executor import can_execute, ExecutionRequest, ExecutionResult
from app.adapters.oanda_account import OandaAccountAdapter
from app.adapters.oanda_order import OandaOrderAdapter

app = FastAPI(title="Execution Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency Injection ---
def get_account_adapter():
    return OandaAccountAdapter()

def get_order_adapter():
    return OandaOrderAdapter()

# --- Models ---
class AccountSummaryResponse(BaseModel):
    balance: str
    NAV: str
    marginAvailable: str
    openTradeCount: int
    openPositionCount: int

class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Instrument e.g., XAU_USD")
    units: float = Field(..., description="Units to trade (positive=long, negative=short)")
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    trade_id: Optional[str] = None

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

@app.get("/account/summary")
async def get_account_summary(adapter: OandaAccountAdapter = Depends(get_account_adapter)):
    try:
        data = adapter.get_summary()
        return AccountSummaryResponse(
            balance=data.get("balance", "0"),
            NAV=data.get("NAV", "0"),
            marginAvailable=data.get("marginAvailable", "0"),
            openTradeCount=data.get("openTradeCount", 0),
            openPositionCount=data.get("openPositionCount", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders", status_code=201)
async def place_order(req: OrderRequest, adapter: OandaOrderAdapter = Depends(get_order_adapter)):
    try:
        response = adapter.place_market_order(
            symbol=req.symbol,
            units=req.units,
            sl_price=req.sl_price,
            tp_price=req.tp_price,
            trade_id=req.trade_id
        )
        
        # Parse relevant fields from OANDA response
        # Note: Response structure depends on fill type (orderFillTransaction)
        fill = response.get("orderFillTransaction")
        if not fill:
             # It might be a pending order or failed immediate fill
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

@app.get("/health")
async def health():
    return {"status": "ok"}