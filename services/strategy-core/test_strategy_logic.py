import pandas as pd
import numpy as np
from app.strategies.bb_stoch_ob_v1.strategy import strategy
from datetime import datetime, timedelta

def test_bb_stoch_ob():
    # Create dummy data
    dates = pd.date_range(start='2026-03-20', periods=100, freq='15min')
    data = pd.DataFrame({
        'open': np.random.uniform(2600, 2700, 100),
        'high': np.random.uniform(2600, 2700, 100),
        'low': np.random.uniform(2600, 2700, 100),
        'close': np.random.uniform(2600, 2700, 100),
        'volume': np.random.uniform(100, 1000, 100)
    }, index=dates)
    
    params = {
        "bb_period": 13,
        "bb_std": 1.5,
        "stoch_k": 9,
        "stoch_d": 3,
        "stoch_oversold": 20,
        "stoch_overbought": 80
    }
    
    print("Running strategy logic...")
    try:
        entries, exits, signal_dict = strategy(data, params)
        print("Success!")
        print(f"Entries: {entries.sum()}")
        print(f"Exits: {exits.sum()}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bb_stoch_ob()
