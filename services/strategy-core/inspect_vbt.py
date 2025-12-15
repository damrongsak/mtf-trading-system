import vectorbt as vbt
import pandas as pd
import numpy as np

price = pd.Series([10, 11, 12, 11, 10], index=pd.date_range("2021-01-01", periods=5))
entries = pd.DataFrame({'a': [True, False, False, False, False], 'b': [False, True, False, False, False]})
exits = pd.DataFrame({'a': [False, False, True, False, False], 'b': [False, False, False, True, False]})
# Broadcast price to match entries
price_df = pd.concat([price]*2, axis=1)
price_df.columns = ['a', 'b']

pf = vbt.Portfolio.from_signals(price_df, entries, exits, freq='1D')

print("DEBUG_VBT_START")
try:
    print(f"pf.total_trades exists: {hasattr(pf, 'total_trades')}")
    if hasattr(pf, 'total_trades'):
         print(f"pf.total_trades is executable: {callable(pf.total_trades)}")
except: pass

try:
    print(f"pf.trades.count exists: {hasattr(pf.trades, 'count')}")
    if hasattr(pf.trades, 'count'):
         print(f"pf.trades.count is executable: {callable(pf.trades.count)}")
         print(f"pf.trades.count value/result: {pf.trades.count() if callable(pf.trades.count) else pf.trades.count}")
except Exception as e:
    print(f"pf.trades.count failed: {e}")

try:
    print(f"pf.positions.count exists: {hasattr(pf.positions, 'count')}")
    if hasattr(pf.positions, 'count'):
         print(f"pf.positions.count value/result: {pf.positions.count() if callable(pf.positions.count) else pf.positions.count}")
except Exception as e:
    print(f"pf.positions.count failed: {e}")
    
print("DEBUG_VBT_END")
