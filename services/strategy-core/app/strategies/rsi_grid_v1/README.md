# MTF-RSI-Grid Strategy (V1)

## Overview
A high-performance mean reversion strategy that uses **VectorBT Broadcasting** to dynamically test multiple RSI parameter combinations in real-time.

## Key Features
- **Dynamic Parameter Grid**: Simultaneously monitors multiple RSI lengths (e.g., 9, 14, 21, 50).
- **Adaptive Selection**: Selects the "Best Fit" parameters based on recent performance (Sharpe/Return).
- **Execution**: Uses the parameters from the winning configuration to generate the current signal.

## Logic
1. **Indicator**: Calculate RSI for `N` windows.
2. **Signal**: 
   - Buy: RSI < Oversold (Dynamic)
   - Sell: RSI > Overbought (Dynamic)
3. **Selection**: 
   - Compare "Hypothetical Returns" of all parameter sets over last `Lookback` candles.
   - Pick the winner.
   - Use winner's signal for the current candle.
