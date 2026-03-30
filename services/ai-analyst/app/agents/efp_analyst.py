import logging
from typing import Dict, Any
import httpx
import pandas as pd
from app.core.config import settings

logger = logging.getLogger(__name__)

class EFPAnalystAgent:
    """
    Agent responsible for calibrating EFP model parameters.
    Analyzes historical arbitrage spreads and trade execution quality.
    """
    def __init__(self):
        self.strategy_core_url = settings.STRATEGY_CORE_URL
        self.api_gateway_url = settings.API_GATEWAY_URL

    async def calibrate_parameters(self, symbol: str = "XAUUSD", timeframe: str = "H1", days: int = 30) -> Dict[str, Any]:
        """
        Main calibration loop:
        1. Resolve the best Gold Futures contract (cTrader GC* or Binance GOLDUSDT).
        2. Fetch historical candles for Spot and resolved Futures.
        3. Calculate EFP spread statistics.
        4. Estimate Mean-Reversion (kappa) and Volatility (sigma).
        5. Update MarketSymbol metadata via API Gateway.
        """
        logger.info(f"Starting EFP calibration for {symbol} ({timeframe}, {days} days)...")
        
        # Map days to candle count (e.g. 30 days * 24 hours = 720)
        tf_multiplier = {"M1": 1440, "M5": 288, "M15": 96, "H1": 24, "H4": 6, "D1": 1}
        mult = tf_multiplier.get(timeframe, 24)
        count = int(days * mult)

        try:
            # 1. Resolve Futures Symbol (cTrader GC* -> Binance GOLDUSDT)
            futures_symbol = await self._resolve_futures_symbol()
            logger.info(f"Resolved futures contract: {futures_symbol}")
            
            # 2. Fetch Candles
            spot_data = await self._fetch_history(symbol, timeframe, count)
            futures_data = await self._fetch_history(futures_symbol, timeframe, count)
            
            # Fallback to Binance if cTrader futures are thin
            if (not futures_data or len(futures_data) < 100) and futures_symbol != "GOLDUSDT":
                logger.warning(f"Thin data for {futures_symbol}, attempting Binance fallback...")
                futures_symbol = "GOLDUSDT"
                futures_data = await self._fetch_history(futures_symbol, timeframe, count)

            if not spot_data or not futures_data:
                logger.error(f"Insufficient data for calibration (Spot: {len(spot_data) if spot_data else 0}, Futures: {len(futures_data) if futures_data else 0})")
                return {"status": "error", "reason": "insufficient_data"}

            # 3. Statistical Analysis
            df_s = pd.DataFrame(spot_data)
            df_f = pd.DataFrame(futures_data)
            
            # Align timestamps
            merged = pd.merge(df_s, df_f, on='timestamp', suffixes=('_s', '_f'))
            if len(merged) < 50:
                logger.error(f"Too few overlapping data points: {len(merged)}")
                return {"status": "error", "reason": "alignment_failure"}

            merged['spread'] = merged['close_f'] - merged['close_s']
            
            vol_e = merged['spread'].std()
            # Crude Mean Reversion Speed approximation
            ac = merged['spread'].autocorr(lag=1)
            kappa_e = 1.0 / ac if (ac and ac < 1.0 and ac > 0.1) else 8.0
            
            # 4. Prepare Updated Metadata
            params = {
                "kappa_e": float(kappa_e),
                "sigma_e": float(vol_e),
                "theta_e": float(merged['spread'].mean()),
                "futures_source": futures_symbol,
                "data_points": len(merged)
            }
            
            logger.info(f"Calibrated Params: {params}")
            
            # 5. Save to MarketSymbol details
            await self._update_symbol_details(symbol, {"efp_params": params})
            
            return {"status": "success", "params": params}
            
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            return {"status": "error", "detail": str(e)}

    async def _resolve_futures_symbol(self) -> str:
        """
        Dynamically finds the best Gold Futures contract.
        Priority: 
        1. Active cTrader symbols starting with 'GC' (ordered by expiry heuristic or active status)
        2. Binance 'GOLDUSDT'
        3. Fallback to 'GCJ26'
        """
        async with httpx.AsyncClient() as client:
            try:
                # Ask API Gateway for all active symbols
                resp = await client.get(f"{self.api_gateway_url}/api/v1/market/symbols")
                if resp.status_code == 200:
                    data = resp.json()
                    symbols = data.get("data", []) if isinstance(data, dict) else data
                    # Filter for GC futures on CTRADER
                    gc_futures = [s['symbol'] for s in symbols if s['symbol'].startswith('GC') and s.get('is_active')]
                    if gc_futures:
                        # Return first active one (usually front month if maintained)
                        return gc_futures[0]
                    
                    # Check for Binance GoldUSDT
                    if any(s['symbol'] == 'GOLDUSDT' for s in symbols):
                        return 'GOLDUSDT'
            except Exception as e:
                logger.warning(f"Discovery failed, using defaults: {e}")
        
        return "GCJ26"

    async def _fetch_history(self, symbol: str, timeframe: str, count: int):
        async with httpx.AsyncClient() as client:
            url = f"{self.strategy_core_url}/api/v1/market/candles"
            try:
                resp = await client.get(url, params={"symbol": symbol, "timeframe": timeframe, "count": count}, timeout=10.0)
                if resp.status_code == 200:
                    return resp.json().get("data", [])
            except Exception as e:
                logger.warning(f"History fetch failed for {symbol}: {e}")
            return None

    async def _update_symbol_details(self, symbol: str, updates: dict):
        """
        Updates the MarketSymbol details via the API Gateway's internal endpoint.
        """
        async with httpx.AsyncClient() as client:
            url = f"{self.api_gateway_url}/api/v1/internal/symbols/{symbol}/details"
            headers = {"X-Internal-Key": settings.INTERNAL_API_KEY}
            
            try:
                resp = await client.patch(url, json=updates, headers=headers)
                if resp.status_code == 200:
                    logger.info(f"Successfully updated details for {symbol}")
                else:
                    logger.error(f"Failed to update details for {symbol}: {resp.text}")
            except Exception as e:
                logger.error(f"Error calling internal update for {symbol}: {e}")

efp_analyst = EFPAnalystAgent()
