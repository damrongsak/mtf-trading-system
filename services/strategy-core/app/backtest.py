import pandas as pd
import vectorbt as vbt
import numpy as np
from sqlalchemy import text
from app.database import engine
from app.schemas import BacktestRequest, BacktestResponse, BacktestMetrics, TradeResult, EquityPoint
from uuid import uuid4

def run_historical_backtest(req: BacktestRequest) -> BacktestResponse:
    # 1. Fetch Data
    # Note: We cast symbols to match DB format if needed. 
    # For now assume req.symbol matches DB.
    
    query = text("""
        SELECT timestamp, open, high, low, close, volume 
        FROM candles 
        WHERE symbol = :symbol 
        AND timeframe = :timeframe 
        AND timestamp >= :start_date 
        AND timestamp <= :end_date
        ORDER BY timestamp ASC
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={
                "symbol": req.symbol,
                "timeframe": req.timeframe,
                "start_date": req.start_date,
                "end_date": req.end_date
            })
    except Exception as e:
        # Fallback for connection errors or schema issues
        print(f"DB Error: {e}")
        return _empty_response(status="FAILED")

    if df.empty:
        return _empty_response()
        
    # Set index
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 2. Strategy Logic (Example: MA Crossover)
    # Default params if not provided
    fast_period = int(req.strategy_params.get("ema_fast", 10))
    slow_period = int(req.strategy_params.get("ema_slow", 20))
    
    # Use Close price
    close_price = df['close'].astype(float)
    
    fast_ma = vbt.MA.run(close_price, fast_period)
    slow_ma = vbt.MA.run(close_price, slow_period)
    
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    
    # 3. Running Portfolio
    # Estimate frequency from data
    freq = None
    if len(df) > 1:
        diff = df.index[1] - df.index[0]
        freq = str(int(diff.total_seconds())) + 'S'

    pf = vbt.Portfolio.from_signals(
        close_price,
        entries,
        exits,
        init_cash=req.initial_capital,
        fees=0.0001,
        freq=freq
    )
    
    # 4. Metrics
    stats = pf.stats()
    
    def get_val(key, default=0.0):
        val = stats.get(key, default)
        if pd.isna(val) or np.isinf(val):
            return default
        return float(val)

    metrics = BacktestMetrics(
        total_return=get_val('Total Return [$]'), # checking vbt docs keys might vary, assuming standard
        total_return_percent=get_val('Total Return [%]'),
        max_drawdown=get_val('Max Drawdown [$]'), 
        max_drawdown_percent=get_val('Max Drawdown [%]'),
        win_rate=get_val('Win Rate [%]'),
        sharpe_ratio=get_val('Sharpe Ratio'),
        total_trades=int(get_val('Total Trades')),
        winning_trades=int(get_val('Winning Trades')),
        losing_trades=int(get_val('Losing Trades'))
    )

    # Note: If keys are missing, we might need to adjust. vbt 0.26 keys:
    # 'Total Return [%]', 'Max Drawdown [%]', 'Win Rate [%]', 'Sharpe Ratio', 'Total Trades', 'Winning Trades', 'Losing Trades'
    # 'Total Return [$]' might not exist, use 'Total Profit'
    
    if 'Total Return [$]' not in stats and 'Total Profit' in stats:
         metrics.total_return = get_val('Total Profit')

    # 5. Trades
    trades_list = []
    # records_readable returns a dataframe
    try:
        readable_trades = pf.trades.records_readable
        # Standard columns: Entry Timestamp, Exit Timestamp, Entry Price, Exit Price, PnL, Return, Direction, Status
        # VBT 0.26 might differ.
        if not readable_trades.empty:
             for idx, row in readable_trades.iterrows():
                trades_list.append(TradeResult(
                    entry_time=row['Entry Timestamp'],
                    exit_time=row['Exit Timestamp'],
                    direction=row['Direction'],
                    entry_price=float(row['Entry Price']),
                    exit_price=float(row['Exit Price']),
                    pnl=float(row['PnL']),
                    pnl_percent=float(row['Return'] * 100)
                ))
    except Exception as e:
        print(f"Error parsing trades: {e}")

    # 6. Equity Curve
    equity_series = pf.value()
    equity_curve = []
    # Downsample if too large (e.g. max 500 points)
    step = max(1, len(equity_series) // 500)
    for ts, val in equity_series.iloc[::step].items():
        equity_curve.append(EquityPoint(
            timestamp=ts.isoformat(),
            value=float(val)
        ))

    return BacktestResponse(
        id=str(uuid4()),
        status="COMPLETED",
        metrics=metrics,
        trades=trades_list,
        equity_curve=equity_curve
    )

def _empty_response(status="COMPLETED"):
    return BacktestResponse(
             id=str(uuid4()),
             status=status,
             metrics=BacktestMetrics(
                 total_return=0.0,
                 total_return_percent=0.0,
                 max_drawdown=0.0,
                 max_drawdown_percent=0.0,
                 win_rate=0.0,
                 sharpe_ratio=0.0,
                 total_trades=0,
                 winning_trades=0,
                 losing_trades=0
             ),
             trades=[],
             equity_curve=[]
        )
