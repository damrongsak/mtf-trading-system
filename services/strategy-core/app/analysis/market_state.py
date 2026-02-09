import pandas as pd
from typing import Dict, Any, Optional
from app.indicators.volatility import detect_volatility_regime
from app.indicators.trend import detect_trend_structure
from app.indicators.volume import calculate_vwap, detect_liquidity_condition
from app.indicators.correlation import calculate_correlation
from app.indicators.positioning import detect_crowding

class MarketStateService:
    @staticmethod
    def analyze_state(
        df: pd.DataFrame, 
        second_df: Optional[pd.DataFrame] = None,
        oi_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Aggregates multiple indicators into a comprehensive market state.
        
        Args:
            df: OHLCV DataFrame
            second_df: Optional second symbol DataFrame for correlation
            oi_data: Optional Open Interest data dict with keys:
                     - call_oi: List[float]
                     - put_oi: List[float]
                     - strikes: List[float]
                     - current_price: float
        """
        if df.empty or len(df) < 50:
            return {"error": "Insufficient data for state analysis"}
            
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']
        
        # 1. Volatility Regime
        regimes = detect_volatility_regime(high, low, close)
        current_regime = regimes.iloc[-1]
        
        # 2. Trend Structure & Squeeze
        trend_df = detect_trend_structure(high, low, close)
        current_trend = trend_df['structure'].iloc[-1]
        is_squeeze = bool(trend_df['is_squeeze'].iloc[-1])
        adx = float(trend_df['adx'].iloc[-1])
        
        # 3. VWAP Distance
        vwap = calculate_vwap(close, volume)
        current_vwap = vwap.iloc[-1]
        vwap_dist = ((close.iloc[-1] - current_vwap) / current_vwap) * 100
        
        # 4. Liquidity Condition
        liquidity = detect_liquidity_condition(volume, close)
        
        # 5. Correlation (if second_df provided)
        correlation_data = None
        if second_df is not None and not second_df.empty:
            correlation_data = calculate_correlation(close, second_df['close'])
        
        # 6. Positioning (if OI data provided)
        positioning_data = None
        if oi_data:
            try:
                positioning_data = detect_crowding(
                    call_oi=oi_data.get('call_oi', []),
                    put_oi=oi_data.get('put_oi', []),
                    strikes=oi_data.get('strikes', []),
                    current_price=oi_data.get('current_price', float(close.iloc[-1]))
                )
            except Exception as e:
                positioning_data = {"error": f"Positioning analysis failed: {str(e)}"}
        
        # 7. Momentum (Simple ROC)
        roc = ((close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]) * 100
        
        result = {
            "volatility_regime": current_regime,
            "trend_structure": current_trend,
            "is_squeeze": is_squeeze,
            "adx": round(adx, 2),
            "vwap_distance_percent": round(vwap_dist, 4),
            "liquidity": liquidity,
            "correlation": correlation_data,
            "positioning": positioning_data,
            "momentum_10p_percent": round(roc, 4),
            "current_price": float(close.iloc[-1]),
            "vwap_price": float(current_vwap)
        }
        
        return result
