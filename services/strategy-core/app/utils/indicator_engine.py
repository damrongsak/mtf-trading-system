import time
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.schemas import (
    BatchIndicatorRequest,
    BatchIndicatorResponse,
    DetailedIndicatorResponse,
    IndicatorType,
)
from app.utils.market_data import fetch_candles_logic
from app.indicators.volatility import calculate_atr_detailed
from app.indicators.momentum import calculate_rsi_detailed, calculate_macd_detailed
from app.indicators.trend import calculate_ema_detailed

logger = logging.getLogger(__name__)


class UniversalIndicatorEngine:
    """
    Institutional batch indicator engine.
    Fetches underlying OHLC data exactly once per request, then fans out to all
    requested indicator calculations. Results are aggregated into a single response.
    """

    DISPATCH_MAP = {
        IndicatorType.ATR:  "_calc_atr",
        IndicatorType.RSI:  "_calc_rsi",
        IndicatorType.EMA:  "_calc_ema",
        IndicatorType.MACD: "_calc_macd",
    }

    # Max candles per indicator type — use highest required value
    CANDLE_LIMIT_MAP = {
        IndicatorType.ATR:  200,
        IndicatorType.RSI:  200,
        IndicatorType.EMA:  300,  # EMA200 needs more history
        IndicatorType.MACD: 400,  # Slow EMA(26) + Signal(9) needs depth
    }

    async def run(
        self,
        req: BatchIndicatorRequest,
        db: Session,
        user_id: str,
    ) -> BatchIndicatorResponse:
        """
        Main entry point. Executes the full batch pipeline.
        Raises HTTPException (404/422/500) on data or calculation failures.
        """
        from fastapi import HTTPException

        batch_start = time.time()

        # 1. Resolve required candle depth (max across all requested indicators)
        required_limit = max(
            self.CANDLE_LIMIT_MAP.get(spec.type, 200)
            for spec in req.indicators
        )

        # 2. Fetch OHLC data once — also returns resolved data_source label
        df, data_source = await fetch_candles_logic(
            db, req.symbol, req.timeframe, user_id, req.fund_id, limit=required_limit
        )
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No candle data found for {req.symbol} [{req.timeframe}]."
                       " Verify symbol is active and data source is configured."
            )

        # 3. Dispatch to each indicator
        results: dict[str, DetailedIndicatorResponse] = {}
        errors: list[str] = []

        for spec in req.indicators:
            indicator_key = spec.type.value  # "atr", "rsi", etc.
            method_name = self.DISPATCH_MAP.get(spec.type)

            if not method_name:
                logger.warning(f"Unsupported indicator type: {spec.type}")
                errors.append(f"Unsupported: {indicator_key}")
                continue

            try:
                calc_fn = getattr(self, method_name)
                result = calc_fn(df, req.symbol, req.timeframe, spec.params, req.fund_id, data_source)
                results[indicator_key] = result
                logger.debug(f"[Engine] Computed {indicator_key} for {req.symbol} [{req.timeframe}]")
            except Exception as e:
                logger.error(f"[Engine] Failed to compute {indicator_key}: {e}", exc_info=True)
                errors.append(f"{indicator_key}: {str(e)}")

        if not results:
            raise HTTPException(
                status_code=500,
                detail=f"All indicator calculations failed. Errors: {errors}"
            )

        batch_latency = (time.time() - batch_start) * 1000

        if errors:
            logger.warning(f"[Engine] Partial batch failure for {req.symbol}: {errors}")

        return BatchIndicatorResponse(
            status="success" if not errors else "partial",
            symbol=req.symbol,
            timeframe=req.timeframe,
            data_source=data_source,
            batch_latency_ms=round(batch_latency, 2),
            results=results,
        )

    # ------------------------------------------------------------------
    # Private dispatch methods
    # ------------------------------------------------------------------

    def _calc_atr(self, df, symbol, timeframe, params, fund_id, data_source):
        window = params.get("window", 14)
        return calculate_atr_detailed(
            high=df["high"], low=df["low"], close=df["close"],
            symbol=symbol, timeframe=timeframe,
            window=window, fund_id=fund_id, data_source=data_source,
        )

    def _calc_rsi(self, df, symbol, timeframe, params, fund_id, data_source):
        window = params.get("window", 14)
        return calculate_rsi_detailed(
            close=df["close"],
            symbol=symbol, timeframe=timeframe,
            window=window, fund_id=fund_id, data_source=data_source,
        )

    def _calc_ema(self, df, symbol, timeframe, params, fund_id, data_source):
        span = params.get("span", 20)
        return calculate_ema_detailed(
            close=df["close"],
            symbol=symbol, timeframe=timeframe,
            span=span, fund_id=fund_id, data_source=data_source,
        )

    def _calc_macd(self, df, symbol, timeframe, params, fund_id, data_source):
        fast   = params.get("fast",   12)
        slow   = params.get("slow",   26)
        signal = params.get("signal",  9)
        return calculate_macd_detailed(
            close=df["close"],
            symbol=symbol, timeframe=timeframe,
            fast=fast, slow=slow, signal=signal,
            fund_id=fund_id, data_source=data_source,
        )


# Module-level singleton — no state, safe for concurrent requests
indicator_engine = UniversalIndicatorEngine()
