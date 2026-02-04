from typing import Dict, Any, List
import pandas as pd
import numpy as np
from arch import arch_model
from app.foundry.base import LogicBlock, BlockType, SignalState
import logging

logger = logging.getLogger(__name__)

class VolatilityGarch(LogicBlock):
    """
    Advanced Volatility Block using GARCH(1,1) to forecast volatility.
    
    Parameters:
    - period (int): Lookback period for fitting the model (default: 1000 candles).
    - p (int): GARCH lag (default: 1).
    - q (int): ARCH lag (default: 1).
    - regime_threshold (float): Annualized vol threshold to flag HIGH_VOL (default: 0.20 or 20%).
    """
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        super().__init__(name, BlockType.VOLATILITY, parameters)
        self.period = self.get_param("period", 1000)
        self.p = self.get_param("p", 1)
        self.q = self.get_param("q", 1)
        self.threshold = self.get_param("regime_threshold", 0.20) # 20% annualized vol

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fits GARCH(1,1) on the provided candle history and forecasts 1-step ahead variance.
        """
        candles = context.get("candles")
        if candles is None:
            return {"state": SignalState.INVALID, "value": 0.0, "reason": "No candles provided"}
            
        try:
            if isinstance(candles, pd.DataFrame):
                closes = candles['close']
            else:
                # Basic dict extraction attempt
                closes = pd.Series([c.close for c in candles])
                
            if len(closes) < self.period:
                 return {"state": SignalState.INVALID, "value": 0.0, "reason": "Insufficient data for GARCH"}

            # Calculate Log Returns * 100 (arch_model prefers scaled returns)
            returns = 100 * np.log(closes / closes.shift(1)).dropna()
            
            # Slice to lookback period
            returns = returns.tail(self.period)
            
            # Fit Model
            # vol='Garch', p=1, q=1 is standard GARCH(1,1)
            model = arch_model(returns, vol='Garch', p=self.p, q=self.q, rescale=False)
            res = model.fit(disp="off", show_warning=False)
            
            # Forecast next period variance
            forecast = res.forecast(horizon=1)
            next_var = forecast.variance.iloc[-1, 0]
            next_vol_daily = np.sqrt(next_var) # This is % daily vol since inputs were returns*100
            
            # Annualize: Daily Vol % * sqrt(252) / 100 (to get back to decimal)
            annualized_vol = (next_vol_daily * np.sqrt(252)) / 100.0
            
            state = SignalState.BULLISH # Low Vol
            if annualized_vol > self.threshold:
                state = SignalState.BEARISH # High Vol (Risk Off)
                
            return {
                "state": state,
                "value": float(annualized_vol),
                "metrics": {
                    "daily_vol_pct": float(next_vol_daily),
                    "annualized_vol": float(annualized_vol),
                    "persistence": float(res.params.get('beta[1]', 0)) # Measuring persistence
                }
            }
            
        except Exception as e:
            logger.error(f"GARCH Block Error: {e}")
            return {"state": SignalState.INVALID, "value": 0.0, "reason": str(e)}

class VolatilityATR(LogicBlock):
    """
    Standard Logic Block for Volatility using ATR.
    Used as a baseline/fallback.
    """
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        super().__init__(name, BlockType.VOLATILITY, parameters)
        self.period = self.get_param("period", 14)
        self.threshold_pips = self.get_param("threshold_pips", 20)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation of ATR logic placeholder
        return {"state": SignalState.NEUTRAL, "value": 0.0}
