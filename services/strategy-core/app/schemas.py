from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ExecutionMode(str, Enum):
    MANUAL = "MANUAL"
    SEMIAUTO = "SEMIAUTO"
    AUTO = "AUTO"

class IndicatorRequest(BaseModel):
    data: List[float]
    params: Dict[str, Any] = {}

class ATRRequest(BaseModel):
    high: List[float]
    low: List[float]
    close: List[float]
    window: int = 14

class IndicatorResponse(BaseModel):
    values: List[Optional[float]]

class MACDResponse(BaseModel):
    macd: List[Optional[float]]
    signal: List[Optional[float]]
    hist: List[Optional[float]]

class BBandsResponse(BaseModel):
    upper: List[Optional[float]]
    middle: List[Optional[float]]
    lower: List[Optional[float]]

class RSIRequest(BaseModel):
    close: List[float]
    window: int = 14

class MACDRequest(BaseModel):
    close: List[float]
    fast: int = 12
    slow: int = 26
    signal: int = 9

class BBandsRequest(BaseModel):
    close: List[float]
    window: int = 20
    alpha: float = 2.0

class SMCRequest(BaseModel):
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: Optional[List[float]] = None

class SMCResponse(BaseModel):
    order_blocks: List[Dict[str, Any]]
    fvgs: List[Dict[str, Any]]
    liquidity_sweeps: List[Dict[str, Any]] = []

# ==========================
# Simulation Schemas
# ==========================

class MarketRegime(BaseModel):
    trend: str # 'NO_TREND', 'UPTREND', 'DOWNTREND'
    volatility: int # 1-10
    noise: str # 'GAUSSIAN', 'FAT_TAIL'

class GridConfig(BaseModel):
    step_size: float
    grid_levels: int
    initial_lot: float
    use_compound: bool
    stop_loss_pct: float

class SimulationRequest(BaseModel):
    regime: MarketRegime
    grid: GridConfig
    iterations: int = 1

class SimulationMetrics(BaseModel):
    total_pnl: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float

class EquityPoint(BaseModel):
    timestamp: str
    value: float

class SimulationResponse(BaseModel):
    id: str
    metrics: SimulationMetrics
    equity_curve: List[EquityPoint]
    status: str

# ==========================
# Backtest Schemas (Real)
# ==========================

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
    target_metric: str = "sharpe_ratio"
    max_iterations: Optional[int] = 100
    early_stopping_rounds: Optional[int] = None
    param_grid: Dict[str, Any]

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    strategy_params: Dict[str, Any] = {}
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    strategy_id: Optional[str] = None
    fund_id: Optional[str] = None
    trading_config_id: Optional[str] = None
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
    equity_curve: List[EquityPoint] = []
    best_params: Optional[Dict[str, Any]] = None
    all_results: Optional[List[Dict[str, Any]]] = None
