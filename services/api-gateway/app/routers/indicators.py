import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional

from app.routers.auth import oauth2_scheme
from app.security import get_current_user
from app.models.user import User
from app.utils.response import success_response
from app.services.internal_client import strategy_client

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/indicators",
    tags=["Institutional Indicators"],
)


class IndicatorSpecGW(BaseModel):
    type: str = Field(..., description="atr | rsi | ema | macd")
    params: Dict[str, Any] = Field(default={}, description="Per-indicator params")


class BatchIndicatorRequestGW(BaseModel):
    """Gateway-facing batch indicator request (mirrors strategy-core schema)."""
    symbol: str = Field("XAUUSD", description="ISO 4217 symbol or macro index (VIX, DXY, US10Y)")
    timeframe: str = Field("H1", description="Timeframe: M1 M5 M15 H1 H4 D1 W1 MN1")
    fund_id: Optional[str] = Field(None, description="Fund UUID for data source isolation")
    indicators: List[IndicatorSpecGW] = Field(..., min_length=1)

    @validator("symbol")
    def sanitize_symbol(cls, v):
        """Sanitize and validate symbol string."""
        s = v.strip().upper()
        if not s:
            raise ValueError("Symbol cannot be empty")
        # Allow alphanumeric, underscores, carets (VIX indices), dots, and hyphens
        import re
        if not re.match(r"^[A-Z0-0\^_\.\-]+$", s):
            raise ValueError("Invalid symbol format. Only alphanumeric, ^, _, ., and - allowed.")
        return s


@router.post(
    "",
    summary="Batch Indicator Engine",
    description="""
Compute multiple technical indicators in a single request.

The system resolves data sources based on `fund_id` (CTRADER for fund symbols, YAHOO_FINANCE for VIX/DXY/US10Y).
OHLC data is fetched exactly **once** regardless of how many indicators are requested.

**Supported types:** `atr`, `rsi`, `ema`, `macd`

**Example:**
```json
{
  "symbol": "XAUUSD",
  "timeframe": "H1",
  "indicators": [
    { "type": "atr",  "params": { "window": 14 } },
    { "type": "ema",  "params": { "span": 200 } },
    { "type": "rsi",  "params": {} },
    { "type": "macd", "params": {} }
  ]
}
```
""",
)
async def calculate_indicators(
    req: BatchIndicatorRequestGW,
    current_user: User = Depends(get_current_user),
):
    """
    Authenticated batch indicator proxy.
    Forwards the request to strategy-core with the authenticated user's ID for data isolation.
    """
    try:
        result = await strategy_client.calculate_indicators(
            payload=req.model_dump(),
            user_id=str(current_user.id),
        )
        return result
    except httpx.HTTPStatusError as e:
        # Forward internal service errors (400, 403, 404) with their original details
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            detail = error_data.get("detail", e.response.text)
        except Exception:
            detail = e.response.text

        logger.warning(f"Indicator engine returned error {status_code}: {detail}")
        raise HTTPException(
            status_code=status_code,
            detail=f"Indicator Engine: {detail}"
        )
    except Exception as e:
        logger.error(f"Gateway indicator proxy failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Indicator service unavailable: {str(e)}",
        )
