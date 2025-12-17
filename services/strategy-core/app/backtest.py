import pandas as pd
from datetime import datetime
import vectorbt as vbt
import numpy as np
from sqlalchemy import text
from app.database import engine
from app.schemas import BacktestRequest, BacktestResponse, BacktestMetrics, TradeResult, EquityPoint
from app.strategy import get_strategy
from uuid import uuid4


def fetch_data_from_db(symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
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
                "symbol": symbol,
                "timeframe": timeframe,
                "start_date": start_date,
                "end_date": end_date
            })
    except Exception as e:
        print(f"DB Error: {e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()
        
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df

def run_historical_backtest(req: BacktestRequest) -> BacktestResponse:
    # 1. Fetch Data
    df = fetch_data_from_db(req.symbol, req.timeframe, req.start_date, req.end_date)
    
    # 2. Strategy Logic
    strategy_name = req.strategy_params.get("name", "ma_crossover")
    strategy_func = get_strategy(strategy_name)
    
    if not strategy_func:
        print(f"ERROR: Strategy '{strategy_name}' not found. Defaulting to ma_crossover.")
        strategy_func = get_strategy("ma_crossover")

    # Use Close price
    close_price = df['close'].astype(float)
    
    # Run Strategy
    entries, exits = strategy_func(close_price, req.strategy_params)

    print(f"INFO: Signals Generated - Entries: {entries.sum().sum()}, Exits: {exits.sum().sum()}")
    
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
        fees=req.fees,
        slippage=req.slippage,
        freq=freq
    )
    
    # 4. Metrics
    stats = pf.stats()
    
    def get_val(key, default=0.0):
        val = stats.get(key, default)
        if pd.isna(val) or np.isinf(val):
            return default
        return float(val)

    first_close = close_price.iloc[0] if len(close_price) > 0 else 1.0
    last_close = close_price.iloc[-1] if len(close_price) > 0 else 1.0
    benchmark_ret = (last_close - first_close) / first_close if first_close != 0 else 0.0

    metrics = BacktestMetrics(
        total_return=get_val('Total Return [$]'), 
        total_return_percent=get_val('Total Return [%]'),
        max_drawdown=get_val('Max Drawdown [$]'), 
        max_drawdown_percent=get_val('Max Drawdown [%]'),
        win_rate=get_val('Win Rate [%]'),
        benchmark_return=float(benchmark_ret * 100), # Return as percentage
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
                    entry_price=float(row['Avg Entry Price']),
                    exit_price=float(row['Avg Exit Price']),
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
