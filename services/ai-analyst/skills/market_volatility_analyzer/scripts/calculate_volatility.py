# /// script
# dependencies = [
#   "pandas",
#   "numpy",
# ]
# ///

import pandas as pd
import numpy as np
import sys
import json

def calculate_vols(prices):
    """
    Prices should be a list of floats.
    """
    df = pd.Series(prices)
    log_returns = np.log(df / df.shift(1))
    
    # Annualized HV (assuming 252 trading days)
    hv20 = log_returns.rolling(window=20).std() * np.sqrt(252)
    hv60 = log_returns.rolling(window=60).std() * np.sqrt(252)
    
    return {
        "current_hv20": hv20.iloc[-1],
        "current_hv60": hv60.iloc[-1],
        "vol_ratio": hv20.iloc[-1] / hv60.iloc[-1] if hv60.iloc[-1] > 0 else 1.0
    }

if __name__ == "__main__":
    # Example input from stdin
    try:
        data = json.load(sys.stdin)
        prices = data.get("prices", [])
        if not prices:
            print(json.dumps({"error": "No prices provided"}))
        else:
            result = calculate_vols(prices)
            print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
