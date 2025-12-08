from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from uuid import UUID
from enum import Enum

class OptimizationMethod(str, Enum):
    GRID = "GRID"
    RANDOM = "RANDOM"
    BAYESIAN = "BAYESIAN"

class ParameterRange(BaseModel):
    start: float
    stop: float
    step: float

class ParameterChoice(BaseModel):
    values: List[Any]

class OptimizationConfig(BaseModel):
    method: OptimizationMethod = OptimizationMethod.GRID
    target_metric: str = "sharpe_ratio" # e.g., "total_return", "sharpe_ratio", "sortino"
    max_iterations: Optional[int] = 100 # For Random/Bayesian
    early_stopping_rounds: Optional[int] = None
    # Map param name to range/choice: {'ema_period': {'start': 10, 'stop': 50, 'step': 10}}
    # We use Union/Dict flexible typing here to allow complex configs
    param_grid: Dict[str, Union[ParameterRange, ParameterChoice, List[Any]]] 

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    strategy_params: Dict[str, Any] = {}
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    
    # Profile References
    strategy_id: Optional[UUID] = None
    fund_id: Optional[UUID] = None
    trading_config_id: Optional[UUID] = None
    
    # Optimization
    optimization: Optional[OptimizationConfig] = None

class TradeResult(BaseModel):
    entry_time: datetime
    exit_time: datetime
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percent: float

class BacktestMetrics(BaseModel):
    total_return: float
    total_return_percent: float
    max_drawdown: float
    max_drawdown_percent: float
    win_rate: float
    sharpe_ratio: Optional[float] = 0.0
    total_trades: int
    winning_trades: int
    losing_trades: int

class BacktestResponse(BaseModel):
    id: str
    status: str
    metrics: Optional[BacktestMetrics] = None
    trades: List[TradeResult] = []
    
    # Optimization Results
    best_params: Optional[Dict[str, Any]] = None
    all_results: Optional[List[Dict[str, Any]]] = None # Summary of all runs
