from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class OrderRequest(BaseModel):
    account_id: Optional[str] = Field(None, description="Legacy field name for broker_account_id")
    broker_account_id: Optional[str] = Field(None, description="The ID of the broker account")
    symbol: str = Field(..., description="Instrument e.g., XAU_USD")
    order_type: str = Field("MARKET", description="MARKET, LIMIT, STOP, STOP_LIMIT")
    side: Optional[str] = Field(None, description="BUY or SELL")
    units: float = Field(..., description="Units to trade (positive=long, negative=short)")
    price: Optional[float] = None # For Limit/Stop
    stop_price: Optional[float] = Field(None, description="Trigger price for STOP/STOP_LIMIT")
    sl_price: Optional[float] = Field(None, description="Stop Loss price")
    tp_price: Optional[float] = Field(None, description="Take Profit price")
    trailing_sl: Optional[bool] = Field(None, description="Trailing Stop Loss")
    comment: Optional[str] = None
    tag: Optional[str] = None
    slippage_pips: Optional[int] = Field(None, description="Slippage tolerance in points")
    base_price: Optional[float] = Field(None, description="Base price for slippage calculation")
    execution_algo: Optional[str] = Field(None, description="Algorithm name (e.g., TWAP, VWAP)")
    algo_params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the algorithm")

class AmendOrderRequest(BaseModel):
    broker_account_id: str
    units: Optional[float] = None
    price: Optional[float] = None
    stop_price: Optional[float] = None
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    trailing_sl: Optional[bool] = None

class AmendPositionRequest(BaseModel):
    broker_account_id: str
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    trailing_sl: Optional[bool] = None
    units: Optional[float] = None # For partial close
