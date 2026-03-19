from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class OrderRequest(BaseModel):
    account_id: Optional[str] = Field(None, description="Legacy field name for broker_account_id")
    broker_account_id: Optional[str] = Field(None, description="The ID of the broker account")
    symbol: str = Field(..., description="Instrument e.g., XAU_USD")
    order_type: str = Field("MARKET", description="MARKET, LIMIT, STOP")
    units: float = Field(..., description="Units to trade (positive=long, negative=short)")
    price: Optional[float] = None # For Limit/Stop
    sl_price: float = Field(..., description="Stop Loss price (MANDATORY)")
    tp_price: float = Field(..., description="Take Profit price (MANDATORY)")
    comment: Optional[str] = None
    tag: Optional[str] = None
