"""
Candle Pydantic schemas for API request/response validation.
Source of truth: specs/01_data_model.yaml -> Candle entity
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


class CandleBase(BaseModel):
    """Base candle schema with common fields."""
    symbol: str = Field(..., max_length=20, description="Trading pair symbol (e.g., XAU/USD)")
    timeframe: str = Field(..., max_length=10, description="Timeframe identifier (15m, 1h, 4h, D)")
    timestamp: datetime = Field(..., description="Candle open timestamp (UTC)")
    open: Decimal = Field(..., description="Opening price", decimal_places=8)
    high: Decimal = Field(..., description="Highest price", decimal_places=8)
    low: Decimal = Field(..., description="Lowest price", decimal_places=8)
    close: Decimal = Field(..., description="Closing price", decimal_places=8)
    volume: Decimal = Field(..., description="Trading volume", decimal_places=8)


class CandleCreate(CandleBase):
    """Schema for creating a new candle."""
    # MTF Indicators (optional at creation, computed later)
    ema_9_4h: Optional[Decimal] = Field(None, description="EMA(9) on 4H timeframe", decimal_places=8)
    ema_200_4h: Optional[Decimal] = Field(None, description="EMA(200) on 4H timeframe", decimal_places=8)
    ema_200_d: Optional[Decimal] = Field(None, description="EMA(200) on Daily timeframe", decimal_places=8)
    atr_14_15m: Optional[Decimal] = Field(None, description="ATR(14) on 15m timeframe", decimal_places=8)
    body_to_wick_ratio: Optional[Decimal] = Field(None, description="Body-to-Wick Ratio (Rv)", decimal_places=4)


class CandleUpdate(BaseModel):
    """Schema for updating indicator values on existing candles."""
    ema_9_4h: Optional[Decimal] = Field(None, decimal_places=8)
    ema_200_4h: Optional[Decimal] = Field(None, decimal_places=8)
    ema_200_d: Optional[Decimal] = Field(None, decimal_places=8)
    atr_14_15m: Optional[Decimal] = Field(None, decimal_places=8)
    body_to_wick_ratio: Optional[Decimal] = Field(None, decimal_places=4)


class CandleResponse(CandleBase):
    """Schema for candle API responses."""
    id: UUID
    ema_9_4h: Optional[Decimal] = None
    ema_200_4h: Optional[Decimal] = None
    ema_200_d: Optional[Decimal] = None
    atr_14_15m: Optional[Decimal] = None
    body_to_wick_ratio: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
