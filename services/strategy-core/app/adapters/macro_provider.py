import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd
from fredapi import Fred
import yfinance as yf

logger = logging.getLogger(__name__)

class MacroProvider:
    """
    MTF Institutional Macro Data Provider.
    Fetches core regime indicators (Real Yields, DXY) from FRED and Yahoo Finance.
    """
    
    def __init__(self, fred_api_key: Optional[str] = None):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            logger.warning("FRED_API_KEY not found. FRED-based macro data will be unavailable.")
            self.fred = None
        else:
            self.fred = Fred(api_key=self.fred_api_key)
            
    async def get_real_yields(self, symbol: str = "DFII10", days: int = 30) -> pd.Series:
        """
        Fetch 10-Year Real Interest Rate (TIPS) from FRED.
        Default: 10-Year (DFII10).
        """
        if not self.fred:
            return pd.Series()
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            data = self.fred.get_series(symbol, observation_start=start_date, observation_end=end_date)
            return data
        except Exception as e:
            logger.error(f"Error fetching real yields from FRED: {e}")
            return pd.Series()
            
    async def get_dxy(self, days: int = 30) -> pd.Series:
        """
        Fetch DXY (US Dollar Index) from Yahoo Finance.
        Ticker: DX-Y.NYB
        """
        try:
            ticker = yf.Ticker("DX-Y.NYB")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            hist = ticker.history(start=start_date, end=end_date)
            if not hist.empty:
                return hist['Close']
            return pd.Series()
        except Exception as e:
            logger.error(f"Error fetching DXY from Yahoo Finance: {e}")
            return pd.Series()

    async def get_macro_context(self) -> Dict[str, Any]:
        """
        Aggregates institutional macro context for liquidity analysis.
        """
        real_yields = await self.get_real_yields()
        dxy = await self.get_dxy()
        
        context = {
            "real_yield_10y": real_yields.iloc[-1] if not real_yields.empty else None,
            "dxy": dxy.iloc[-1] if not dxy.empty else None,
            "real_yield_trend": "UP" if len(real_yields) > 1 and real_yields.iloc[-1] > real_yields.iloc[-2] else "DOWN",
            "dxy_trend": "UP" if len(dxy) > 1 and dxy.iloc[-1] > dxy.iloc[-2] else "DOWN",
            "updated_at": datetime.now().isoformat()
        }
        
        return context
