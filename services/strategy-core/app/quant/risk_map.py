import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.indicators.smc import analyze_smc
from app.indicators.volatility import detect_volatility_regime, calculate_atr
from app.indicators.trend import detect_trend_structure
from app.analysis.market_regime import detect_regime, MarketRegime
from app.indicators.garch_engine import garch_engine

logger = logging.getLogger(__name__)

class RiskMapEngine:
    """
    Institutional Quant Layer: Risk Map Engine.
    Aggregates Structural, Volatility, Liquidity (Proxy), and Probability layers.
    """

    def __init__(self):
        self.weights = {
            "structural": 0.4,
            "volatility": 0.3,
            "regime": 0.3
        }

    def compute_risk_score(self, 
                          symbol: str, 
                          df: pd.DataFrame, 
                          timeframe: str = "H1") -> Dict[str, Any]:
        """
        Generates a comprehensive Risk Score Surface for the current price level.
        """
        if df.empty or len(df) < 50:
            return {"error": "Insufficient data"}

        last_close = float(df['close'].iloc[-1])
        
        # 1. Structural Layer (SMC)
        smc_data = analyze_smc(df, symbol=symbol, timeframe=timeframe)
        structure_risk = self._calculate_structural_risk(smc_data, last_close)
        
        # 2. Volatility Layer
        vol_regime = detect_volatility_regime(df['high'], df['low'], df['close']).iloc[-1]
        vol_risk = self._calculate_volatility_risk(vol_regime)
        
        # 3. Probability Layer (Regime)
        regime = detect_regime(df)
        if not regime:
            regime = MarketRegime.RANGING # Default fallback
        regime_risk = self._calculate_regime_risk(regime)
        
        # 4. Liquidity Layer (Gamma Proxy)
        gamma_bias = self._estimate_gamma_proxy(df, vol_regime)
        
        # 5. Composite Risk Score
        # Defensive check for NaN
        composite_score = (
            float(structure_risk) * self.weights["structural"] +
            float(vol_risk) * self.weights["volatility"] +
            float(regime_risk) * self.weights["regime"]
        )
        if np.isnan(composite_score):
            composite_score = 0.5
        
        # 6. Edge Score (Signal Quality)
        edge_score = self._calculate_edge_score(smc_data, regime, last_close)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "price": last_close,
            "composite_risk_score": round(composite_score, 2),
            "edge_score": round(edge_score, 2),
            "layers": {
                "structural_risk": structure_risk,
                "volatility_risk": vol_risk,
                "regime_risk": regime_risk,
                "gamma_bias": gamma_bias
            },
            "context": {
                "regime": regime,
                "volatility_regime": vol_regime,
                "institutional_bias": smc_data.get("institutional_bias", "NEUTRAL")
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def _calculate_structural_risk(self, smc_data: Dict[str, Any], price: float) -> float:
        """
        Higher risk if near Supply, Lower risk if near Demand.
        """
        bias = smc_data.get("institutional_bias", "NEUTRAL")
        if bias == "BULLISH":
            return 0.3  # Low structural risk for buying
        elif bias == "BEARISH":
            return 0.7  # High structural risk for buying (near supply)
        return 0.5

    def _calculate_volatility_risk(self, vol_regime: str) -> float:
        """
        Panic/Expanding volatility = High Risk.
        """
        mapping = {
            "Panic": 1.0,
            "Expanding": 0.8,
            "Stable": 0.5,
            "Low": 0.3
        }
        return mapping.get(vol_regime, 0.5)

    def _calculate_regime_risk(self, regime: MarketRegime) -> float:
        """
        Trending = Lower risk, Unstable/Ranging = Higher risk for trend following.
        """
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            return 0.3
        elif regime == MarketRegime.RANGING:
            return 0.7
        return 0.9  # UNSTABLE

    def _estimate_gamma_proxy(self, df: pd.DataFrame, vol_regime: str) -> str:
        """
        Proxy for Gamma:
        Large Range Breakout + Rising Volatility -> Negative Gamma condition (Acceleration)
        Narrow Range + Falling Volatility -> Positive Gamma condition (Reversion)
        """
        if len(df) < 5:
            return "NEUTRAL"
        
        last_body = abs(df['close'].iloc[-1] - df['open'].iloc[-1])
        avg_body = abs(df['close'] - df['open']).rolling(5).mean().iloc[-1]
        
        if vol_regime in ["Expanding", "Panic"] and last_body > avg_body * 1.5:
            return "NEGATIVE" # Breakout acceleration bias
        elif vol_regime == "Low":
            return "POSITIVE" # Mean reversion bias
            
        return "NEUTRAL"

    def _calculate_edge_score(self, smc_data: Dict[str, Any], regime: MarketRegime, price: float) -> float:
        """
        Edge Score = Confluence of SMA + Trend + Momentum.
        """
        bias = smc_data.get("institutional_bias", "NEUTRAL")
        confluence_count = len(smc_data.get("meta", {}).get("bullish_confluence", []))
        
        score = 0.5
        
        # Bias weight
        if bias != "NEUTRAL":
            score += 0.2
            
        # Confluence weight
        score += min(0.3, confluence_count * 0.1)
        
        # Regime alignment
        if (bias == "BULLISH" and regime == MarketRegime.TRENDING_UP) or \
           (bias == "BEARISH" and regime == MarketRegime.TRENDING_DOWN):
            score += 0.2
        
        return min(1.0, score)

risk_map_engine = RiskMapEngine()
