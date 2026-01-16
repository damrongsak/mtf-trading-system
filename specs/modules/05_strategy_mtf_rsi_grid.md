# Strategy Specification: MTF-RSI-Grid (VectorBT Optimized)

## 1. Overview
The **MTF-RSI-Grid** strategy is a high-performance mean reversion strategy designed to leverage **VectorBT's** broadcasting capabilities. Instead of relying on a single static parameter set (e.g., RSI 14, Overbought 70), it dynamically tests multiple parameter combinations in real-time (or quasi-real-time) to adapt to changing market volatility conditions.

## 2. Core Logic

### 2.1. Vectorized Indicators
The strategy calculates RSI for a broadcasting grid of parameters:
- **RSI Lengths**: Range `[5, 10, 14, 21, 50]`
- **Oversold Thresholds**: Range `[20, 25, 30, 35]`
- **Overbought Thresholds**: Range `[65, 70, 75, 80]`

### 2.2. Signal Generation
For each combination (window, thresholds), a signal vector is generated:
- **Long Entry**: RSI < Oversold Threshold
- **Long Exit**: RSI > Overbought Threshold
- **Short Entry**: RSI > Overbought Threshold
- **Short Exit**: RSI < Oversold Threshold

### 2.3. Optimization & Selection
Unlike traditional strategies that pick one winner *historically*, this strategy can run in two modes:
1.  **Ensemble Mode**: Execute trades if > 50% of the parameter grid agrees.
2.  **Best-Fit Mode**: Select the parameter set that performed best over the last `N` periods (Walk-Forward Optimization) and use its signal for the next candle.

## 3. Implementation Details

### 3.1. Class Structure
- **Class Name**: `MtfRsiGridStrategy`
- **Location**: `services/strategy-core/app/strategies/rsi_grid_v1`
- **Inheritance**: `BaseStrategy` (or `PluginInterface`)

### 3.2. VectorBT Pipeline
1.  **Data Ingestion**: Fetch OHLCV.
2.  **Indicator Run**: `vbt.RSI.run(close, window=windows_array)` -> Returns `(Rows x N_Windows)` matrix.
3.  **Signal Logic**:
    ```python
    entries = rsi < oversold_grid
    exits = rsi > overbought_grid
    ```
4.  **Portfolio Simulation**: `vbt.Portfolio.from_signals(..., broadcast_named_args=True)`
5.  **Metric Extraction**: Calculate Sharpe/WinRate for each column.
6.  **Selection**: Pick column with max Sharpe.

## 4. Configuration Schema
```json
{
  "symbol": "XAU/USD",
  "timeframes": ["15m"],
  "rsi_windows": [14, 21],
  "thresholds": {
    "oversold": [30, 25],
    "overbought": [70, 75]
  },
  "selection_metric": "sharpe_ratio",
  "lookback_period": 100
}
```

## 5. Risk Management
- **Stop Loss**: Fixed % or ATR-based (calculated per grid or globally).
- **Take Profit**: Signal-based exit or Fixed R:R.
