from pydantic import BaseModel
from typing import List, Dict, Any, Optional

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

