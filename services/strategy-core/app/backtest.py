import pandas as pd
from datetime import datetime
import numpy as np
from sqlalchemy import text
from app.database import engine
from app.schemas import BacktestRequest, BacktestResponse, BacktestMetrics, TradeResult, EquityPoint, StrategyBacktestRequest
from app.strategy import get_strategy # Keep for built-ins
from app.registry import StrategyRegistry # Access new registry methods
from uuid import uuid4
import ast
import multiprocessing
import traceback
from typing import Tuple, Dict, Any
import logging
import inspect
from app.analysis.optimizer import PortfolioOptimizer
from app.features.quant_features import QuantreoFeatures
from app.analysis.metrics import calculate_sortino, calculate_alpha_beta, calculate_information_ratio
from app.analysis.benchmark import BenchmarkService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_strategy_sync(name: str):
    # Adapter to try Registry first, then built-in
    s = StrategyRegistry.get_strategy_sync(name)
    if s: return s
    # Try built-in
    return get_strategy(name)

def check_safety(code: str) -> Tuple[bool, str]:
    """
    Basic static analysis to reject obviously dangerous code.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name.split('.')[0] in ['os', 'sys', 'subprocess', 'shutil', 'pickle', 'importlib', 'builtins']:
                    return False, f"Forbidden import: {alias.name}"
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

def run_historical_backtest(req: BacktestRequest) -> BacktestResponse:
    """
    Run backtest on historical data from DB.
    """
    try:
        # 1. Fetch Data
        from app.database import SessionLocal
        from app.utils.helpers import resolve_market_symbol
        
        db = SessionLocal()
        try:
            ms = resolve_market_symbol(db, req.symbol)
            if not ms:
                print(f"ERROR: MarketSymbol not found for {req.symbol}")
                return _empty_response(status="ERROR_SYMBOL_NOT_FOUND")
            ms_id = str(ms.id)
        finally:
            db.close()

        df = fetch_data_from_db(ms_id, req.timeframe, req.start_date, req.end_date)
        
        if df.empty:
            logger.warning(f"No data found for {req.symbol} ({req.timeframe})")
            return _empty_response(status="ERROR_NO_DATA")
        
        # 2. Strategy Logic
        strategy_name = req.strategy_params.get("name")
        if not strategy_name:
            strategy_name = req.strategy_id or "ma_crossover"
        
        # Resolve UUID
        try:
            import uuid
            uuid.UUID(str(strategy_name))
            from app.models.strategy import Strategy
            db = SessionLocal()
            try:
                strat_record = db.query(Strategy).filter(Strategy.id == strategy_name).first()
                if strat_record:
                    strategy_name = strat_record.template_id
                    req.strategy_params = {**(strat_record.config_json or {}), **req.strategy_params}
            finally:
                db.close()
        except:
            pass

        logger.info(f"Running strategy: {strategy_name}")
        
        strategy_func = get_strategy_sync(strategy_name)
        if not strategy_func:
            strategy_func = get_strategy(strategy_name)
        if not strategy_func:
            strategy_func = get_strategy("ma_crossover")

        # Use Close price for VBT logic
        close_price = df['close'].astype(float)
        
        # Run Strategy
        sig = inspect.signature(strategy_func)
        if 'params' in sig.parameters:
             result = strategy_func(df, params=req.strategy_params)
        else:
             try:
                 result = strategy_func(df, **req.strategy_params)
             except:
                 result = strategy_func(df)

        # Unpack
        if isinstance(result, tuple):
            entries = result[0]
            exits = result[1]
        else:
            entries = result
            exits = pd.Series(False, index=df.index)

        if entries is None: entries = pd.Series(0, index=df.index)
        if exits is None: exits = pd.Series(0, index=df.index)

        # Vectorbt logic
        long_entries = (entries == 1).astype(bool)
        long_exits = (exits == 1).astype(bool)
        short_entries = (entries == -1).astype(bool)
        short_exits = (exits == -1).astype(bool)

        if long_entries.sum() == 0 and short_entries.sum() == 0:
            return _empty_response(status="COMPLETED_NO_TRADES")

        # 3. Portfolio
        import vectorbt as vbt
        freq = None
        if len(df) > 1:
            freq = str(int((df.index[1] - df.index[0]).total_seconds())) + 'S'

        pf = vbt.Portfolio.from_signals(
            close_price,
            entries=long_entries,
            exits=long_exits,
            short_entries=short_entries,
            short_exits=short_exits,
            init_cash=req.initial_capital,
            fees=req.fees,
            slippage=req.slippage,
            freq=freq
        )
        
        # 4. Metrics
        logger.info("Calculating portfolio stats...")
        stats = pf.stats()
        logger.info("Stats calculated successfully.")
        
        def get_val(key, default=0.0):
            val = stats.get(key, default)
            return float(val) if not (pd.isna(val) or np.isinf(val)) else default

        logger.info("Parsing metrics...")
        metrics = BacktestMetrics(
            total_return=get_val('Total Return [$]', get_val('Total Profit')),
            total_return_percent=get_val('Total Return [%]'),
            max_drawdown=get_val('Max Drawdown [$]'),
            max_drawdown_percent=get_val('Max Drawdown [%]'),
            win_rate=get_val('Win Rate [%]'),
            benchmark_return=0.0,
            sharpe_ratio=get_val('Sharpe Ratio'),
            total_trades=int(get_val('Total Trades')),
            winning_trades=int(get_val('Winning Trades')),
            losing_trades=int(get_val('Losing Trades')),
            candle_count=len(df)
        )
        logger.info("Metrics parsed.")

        # 5. Trades
        logger.info("Parsing trades...")
        trades_list = []
        try:
            rt = pf.trades.records_readable
            if not rt.empty:
                for _, row in rt.iterrows():
                    trades_list.append(TradeResult(
                        entry_time=str(row['Entry Timestamp']),
                        exit_time=str(row['Exit Timestamp']),
                        direction=str(row['Direction']),
                        entry_price=float(row['Avg Entry Price']),
                        exit_price=float(row['Avg Exit Price']),
                        pnl=float(row['PnL']),
                        pnl_percent=float(row['Return'] * 100),
                        size=float(row.get('Size', 0))
                    ))
        except Exception as e: 
            logger.error(f"Trade parsing error: {e}")
        logger.info(f"Trades parsed: {len(trades_list)}")

        # 6. Equity
        logger.info("Parsing equity curve...")
        equity_series = pf.value()
        equity_curve = []
        step = max(1, len(equity_series)//500)
        for ts, val in equity_series.iloc[::step].items():
            equity_curve.append(EquityPoint(timestamp=str(ts), value=float(val)))
        logger.info(f"Equity curve parsed: {len(equity_curve)} points")

        logger.info("Constructing final response...")
        response = BacktestResponse(
            id=str(uuid4()),
            status="COMPLETED",
            metrics=metrics,
            trades=trades_list,
            equity_curve=equity_curve
        )
        logger.info("Response constructed.")
        return response
    except Exception as e:
        logger.error(f"Backtest Error: {e}\n{traceback.format_exc()}")
        return _empty_response(status=f"ERROR: {str(e)}")

def _empty_response(status="COMPLETED"):
    return BacktestResponse(
        id=str(uuid4()),
        status=status,
        metrics=BacktestMetrics(total_return=0, total_return_percent=0, max_drawdown=0, 
                               max_drawdown_percent=0, win_rate=0, benchmark_return=0,
                               sharpe_ratio=0, total_trades=0, winning_trades=0,
                               losing_trades=0, candle_count=0),
        trades=[],
        equity_curve=[]
    )
