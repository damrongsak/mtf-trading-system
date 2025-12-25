import pandas as pd
from datetime import datetime
import vectorbt as vbt
import numpy as np
from sqlalchemy import text
from app.database import engine
from app.schemas import BacktestRequest, BacktestResponse, BacktestMetrics, TradeResult, EquityPoint, StrategyBacktestRequest
from app.strategy import get_strategy
from uuid import uuid4
import ast
import multiprocessing
import traceback
from typing import Tuple, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_safety(code: str) -> Tuple[bool, str]:
    """
    Basic static analysis to reject obviously dangerous code.
    Blocks: import os, sys, subprocess, etc.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"

    for node in ast.walk(tree):
        # 1. Block imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name.split('.')[0] in ['os', 'sys', 'subprocess', 'shutil', 'pickle', 'importlib', 'builtins']:
                    return False, f"Forbidden import: {alias.name}"
        
        # 2. Block __import__ and open/eval/exec
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ['open', 'eval', 'exec', '__import__', 'globals', 'locals']:
                     return False, f"Forbidden function call: {node.func.id}"
    
    return True, ""


def fetch_data_from_db(market_symbol_id: str, timeframe: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    query = text("""
        SELECT timestamp, open, high, low, close, volume 
        FROM candles 
        WHERE market_symbol_id = :market_symbol_id
        AND timeframe = :timeframe 
        AND timestamp >= :start_date 
        AND timestamp <= :end_date
        ORDER BY timestamp ASC
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={
                "market_symbol_id": market_symbol_id,
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


def _worker_logic(req_dict: Dict[str, Any], df: pd.DataFrame, result_queue: multiprocessing.Queue):
    """
    Isolated execution logic for the worker process.
    """
    try:
        # Re-import libraries in the worker process context if needed (though usually inherited on fork)
        # On spawn (non-Unix), imports are needed. Docker is Linux (fork), but safe to be explicit or just rely on module level imports.
        
        # 2. Execute Custom Code
        local_scope = {}
        exec_globals = {
            'pd': pd,
            'np': np,
            'vbt': vbt,
            'vectorbt': vbt
        }
        
        exec(req_dict['code'], exec_globals, local_scope)
        
        if 'strategy' not in local_scope:
            result_queue.put({'status': 'ERROR', 'message': "Function 'strategy' not found in code."})
            return

        strategy_func = local_scope['strategy']
        entries, exits = strategy_func(df)
        
        # 3. Running Portfolio
        freq = None
        if len(df) > 1:
            diff = df.index[1] - df.index[0]
            freq = str(int(diff.total_seconds())) + 'S'

        close_price = df['close'].astype(float)
        
        pf = vbt.Portfolio.from_signals(
            close_price,
            entries,
            exits,
            init_cash=req_dict['initial_capital'],
            fees=req_dict['fees'],
            slippage=req_dict['slippage'],
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

        # Debug: Log available stats keys
        print(f"DEBUG: VBT Stats Keys: {stats.index.tolist()}")

        total_return = float(pf.total_profit()) if hasattr(pf, 'total_profit') else get_val('Total Profit')
        # max_drawdown in vbt is usually absolute dollar amount
        max_dd = float(pf.max_drawdown()) if hasattr(pf, 'max_drawdown') else abs(float(pf.stats().get('Max Drawdown [$]', 0.0)))

        metrics = BacktestMetrics(
            total_return=total_return, 
            total_return_percent=get_val('Total Return [%]'),
            max_drawdown=max_dd, 
            max_drawdown_percent=get_val('Max Drawdown [%]'),
            win_rate=get_val('Win Rate [%]'),
            benchmark_return=float(benchmark_ret * 100),
            sharpe_ratio=get_val('Sharpe Ratio'),
            total_trades=int(get_val('Total Trades')),
            winning_trades=int(get_val('Winning Trades')),
            losing_trades=int(get_val('Losing Trades')),
            candle_count=len(df)
        )
        
        if 'Total Return [$]' not in stats and 'Total Profit' in stats:
             metrics.total_return = get_val('Total Profit')

        # 5. Trades
        trades_list = []
        readable_trades = pf.trades.records_readable
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

        # 6. Equity Curve
        equity_series = pf.value()
        equity_curve = []
        step = max(1, len(equity_series) // 500)
        for ts, val in equity_series.iloc[::step].items():
            equity_curve.append(EquityPoint(
                timestamp=ts.isoformat(),
                value=float(val)
            ))

        # 7. Interactive Plot (Plotly JSON)
        # pf.plot() returns a Plotly FigureWidget/Figure
        # We serialize it to JSON for the frontend
        try:
            fig = pf.plot()
            plot_json = fig.to_json()
        except Exception as plot_err:
            print(f"Error generating plot: {plot_err}")
            plot_json = None

        result_queue.put({
            'status': 'SUCCESS',
            'metrics': metrics,
            'trades': trades_list,
            'equity_curve': equity_curve,
            'plot_json': plot_json
        })
        
    except Exception as e:
        result_queue.put({'status': 'ERROR', 'message': str(e)})


def run_custom_backtest(req: StrategyBacktestRequest) -> BacktestResponse:
    # 0. Safety Check
    safe, reason = check_safety(req.code)
    if not safe:
        return _empty_response(status=f"SECURITY_VIOLATION: {reason}")

    # 1. Fetch Data
    from app.database import SessionLocal
    from app.utils.helpers import resolve_market_symbol_id
    
    db = SessionLocal()
    try:
        ms_id = resolve_market_symbol_id(db, req.symbol)
        if not ms_id:
            return _empty_response(status="ERROR_SYMBOL_NOT_FOUND")
    finally:
        db.close()

    logger.info(f"Custom Backtest Request: Symbol={req.symbol}, TF={req.timeframe}, Start={req.start_date}, End={req.end_date}")

    # Normalize Timeframe (Frontend '15m' -> DB 'M15', etc.)
    tf_map = {
        '1m': 'M1', '5m': 'M5', '15m': 'M15', '30m': 'M30',
        '1h': 'H1', '4h': 'H4', 
        '1d': 'D', '1w': 'W'
    }
    normalized_tf = tf_map.get(str(req.timeframe).lower(), str(req.timeframe))
    # Handle implicit casing if not in map (e.g. m1 -> M1)
    if normalized_tf not in tf_map.values():
         # Fallback to uppercase if it looks like a standard timeframe
         normalized_tf = normalized_tf.upper()

    logger.info(f"Normalized Timeframe: {req.timeframe} -> {normalized_tf}")

    df = fetch_data_from_db(ms_id, normalized_tf, req.start_date, req.end_date)
    
    logger.info(f"Fetched URL Data Shape: {df.shape}")

    if df.empty:
        logger.warning("No data found for the specified parameters.")
        return _empty_response(status="ERROR_NO_DATA")

    # 2. Run in Isolated Process
    # Prepare serializable request dict
    req_dict = {
        'code': req.code,
        'initial_capital': req.initial_capital,
        'fees': req.fees,
        'slippage': req.slippage
    }

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_worker_logic, args=(req_dict, df, queue))
    
    try:
        process.start()
        # 300 second timeout for extreme testing
        result = queue.get(timeout=300)
        process.join()
    except multiprocessing.queues.Empty:
        process.terminate()
        process.join()
        return _empty_response(status="ERROR_TIMEOUT: Strategy execution exceeded 90 seconds")
    except Exception as e:
        process.terminate()
        return _empty_response(status=f"SYSTEM_ERROR: {e}")

    # 3. Process Result
    if result['status'] == 'ERROR':
        return _empty_response(status=f"EXECUTION_ERROR: {result['message']}")
    
    return BacktestResponse(
        id=str(uuid4()),
        status="COMPLETED",
        metrics=result['metrics'],
        trades=result['trades'],
        equity_curve=result['equity_curve'],
        plot_json=result.get('plot_json')
    )



def run_historical_backtest(req: BacktestRequest) -> BacktestResponse:
    # 1. Fetch Data
    from app.database import SessionLocal
    from app.utils.helpers import resolve_market_symbol_id
    
    db = SessionLocal()
    try:
        ms_id = resolve_market_symbol_id(db, req.symbol)
        if not ms_id:
            print(f"ERROR: MarketSymbol not found for {req.symbol}")
            return _empty_response(status="ERROR_SYMBOL_NOT_FOUND")
    finally:
        db.close()

    df = fetch_data_from_db(ms_id, req.timeframe, req.start_date, req.end_date)
    
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
        losing_trades=int(get_val('Losing Trades')),
        candle_count=len(df)
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
                 losing_trades=0,
                 candle_count=0
             ),
             trades=[],
             equity_curve=[]
        )
