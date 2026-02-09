import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def calculate_correlation(series_a: pd.Series, series_b: pd.Series, window: int = 20) -> Dict[str, Any]:
    """
    Calculate rolling and current correlation between two price series.
    """
    if len(series_a) < window or len(series_b) < window:
         return {"error": "Insufficient data for correlation"}
         
    # Align series
    df = pd.DataFrame({'a': series_a, 'b': series_b}).dropna()
    
    if len(df) < window:
        return {"error": "Insufficient overlapping data"}
        
    rolling_corr = df['a'].rolling(window=window).corr(df['b'])
    current_corr = rolling_corr.iloc[-1]
    
    # Classify Regime
    if current_corr > 0.7:
        regime = "Strong Positive"
    elif current_corr > 0.3:
        regime = "Positive"
    elif current_corr < -0.7:
        regime = "Strong Negative (Inverse)"
    elif current_corr < -0.3:
        regime = "Negative (Inverse)"
    else:
        regime = "Decoupled / Uncorrelated"
        
    return {
        "correlation": round(float(current_corr), 4) if np.isfinite(current_corr) else None,
        "regime": regime,
        "rolling_avg": round(float(rolling_corr.mean()), 4) if np.isfinite(rolling_corr.mean()) else None
    }
