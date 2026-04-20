import pandas as pd
import yfinance as yf
from fredapi import Fred
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class MacroEngine:
    """
    Fetches and processes macro data (Real Yields, DXY, Net Liquidity)
    for cross-market stress testing.
    """
    
    def __init__(self, fred_api_key: Optional[str] = None):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            logger.warning("FRED_API_KEY not found. MacroEngine will have limited functionality.")
        else:
            self.fred = Fred(api_key=self.fred_api_key)

    def get_real_yields(self) -> Optional[float]:
        """
        Fetch the 10-Year Real Interest Rate (T10YIE - TIPs spread or REAIN)
        Commonly: DFII10 (10-Year Treasury Inflation-Indexed Security)
        """
        if not self.fred_api_key: return None
        try:
            data = self.fred.get_series('DFII10')
            if not data.empty:
                return float(data.iloc[-1])
        except Exception as e:
            logger.error(f"Error fetching Real Yields from FRED: {e}")
        return None

    def get_dxy_index(self) -> Optional[float]:
        """
        Fetch the US Dollar Index (DXY) from Yahoo Finance.
        """
        try:
            dxy = yf.Ticker("DX-Y.NYB")
            hist = dxy.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Error fetching DXY from Yahoo Finance: {e}")
        return None

    def get_macro_snapshot(self) -> Dict[str, Optional[float]]:
        """
        Returns a snapshot of key macro drivers for Gold.
        """
        return {
            "real_yields": self.get_real_yields(),
            "dxy": self.get_dxy_index(),
            "timestamp": pd.Timestamp.now().isoformat()
        }

macro_engine = MacroEngine()
