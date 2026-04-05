"""
Institutional Indicator Engine — Router (v3.0)

Single unified endpoint:
    POST /api/v1/indicators

Replaces the fragmented:
    POST /api/v1/calculate/v2/atr
    POST /api/v1/calculate/v2/rsi
    POST /api/v1/calculate/v2/ema
    POST /api/v1/calculate/v2/macd
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from sqlalchemy.orm import Session

from app.schemas import BatchIndicatorRequest, BatchIndicatorResponse
from app.database import SessionLocal
from app.utils.indicator_engine import indicator_engine

router = APIRouter(
    prefix="/indicators",
    tags=["Institutional Indicators"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=BatchIndicatorResponse,
    summary="Batch Indicator Engine",
    description="""
Compute one or more technical indicators for a given symbol/timeframe in a single request.

**Key behaviours:**
- Underlying OHLC data is fetched **once** from the database, regardless of how many indicators are requested.
- Data source is automatically resolved based on the `fund_id` context (CTRADER for fund symbols, YAHOO_FINANCE for macro indices like VIX/DXY).
- Each result contains full white-box metadata (formula, source, latency) and an AI-ready interpretation (bias, summary, strength).

**Supported indicator types:**

| type | default params |
|------|---------------|
| `atr` | `window=14` |
| `rsi` | `window=14` |
| `ema` | `span=20` |
| `macd` | `fast=12, slow=26, signal=9` |

**Example request:**
```json
{
  "symbol": "XAUUSD",
  "timeframe": "H1",
  "fund_id": "optional-uuid",
  "indicators": [
    { "type": "atr",  "params": { "window": 14 } },
    { "type": "ema",  "params": { "span": 200 } },
    { "type": "rsi",  "params": {} },
    { "type": "macd", "params": { "fast": 12, "slow": 26, "signal": 9 } }
  ]
}
```
""",
)
async def calculate_indicators_batch(
    req: BatchIndicatorRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """
    Institutional batch indicator endpoint.
    Resolves data source, fetches OHLC candles once, then dispatches all
    requested indicator calculations via the UniversalIndicatorEngine.
    """
    user_id = x_user_id or "system"
    return await indicator_engine.run(req, db, user_id)
