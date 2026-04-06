from pydantic import BaseModel, Field
try:
    from pydantic import field_validator as validator
except ImportError:
    from pydantic import validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
import re

class IndicatorMetadata(BaseModel):
    parameters: Dict[str, Any] = {}
    formula: str = ""
    data_source: str = "CTRADER"
    resolved_symbol: str = ""
    calc_latency_ms: float = 0.0
    fund_context: Optional[str] = None
    timeframe: str = "H1"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class IndicatorInterpretation(BaseModel):
    summary: str = ""
    bias: str = "NEUTRAL" # BULLISH, BEARISH, NEUTRAL
    strength: float = 0.5 # 0.0 to 1.0
    ai_advice: str = ""
    signals: List[Dict[str, Any]] = []

class DetailedIndicatorResponse(BaseModel):
    status: str = "success"
    values: List[Optional[float]]
    meta: IndicatorMetadata
    interpretation: IndicatorInterpretation

class ExecutionMode(str, Enum):
    MANUAL = "MANUAL"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    AUTO = "AUTO"

# ==========================
# Institutional Indicator Engine — Batch API (v3.0)
# POST /api/v1/indicators
# ==========================

class IndicatorType(str, Enum):
    ATR  = "atr"
    RSI  = "rsi"
    EMA  = "ema"
    MACD = "macd"

class IndicatorSpec(BaseModel):
    """Specification for a single indicator in a batch request."""
    type: IndicatorType
    params: Dict[str, Any] = Field(
        default={},
        description=(
            "Per-indicator parameters. "
            "atr/rsi: {window: int} | "
            "ema: {span: int} | "
            "macd: {fast: int, slow: int, signal: int}"
        )
    )

class BatchIndicatorRequest(BaseModel):
    """
    Unified batch indicator request.
    Fetches candle data once and computes all requested indicators in a single round-trip.
    """
    symbol: str = Field("XAUUSD", description="ISO 4217 symbol, or known macro index (VIX, DXY, US10Y)")
    timeframe: str = Field("H1", description="Timeframe: M1 M5 M15 H1 H4 D1 W1 MN1")
    fund_id: Optional[str] = Field(None, description="Fund UUID for institutional data isolation")
    indicators: List[IndicatorSpec] = Field(
        ...,
        description="List of indicator specs to calculate in this batch.",
        min_length=1
    )

    @validator('symbol')
    def validate_symbol_iso(cls, v):
        if v in ["VIX", "DXY", "US10Y", "US02Y", "SPX500", "NAS100"]:
            return v
        v = v.upper().replace("/", "").replace("_", "")
        if not re.match(r"^[A-Z]{3,8}$", v):
            raise ValueError("Symbol must be valid uppercase ISO (e.g. EURUSD) or known index.")
        return v

class BatchIndicatorResponse(BaseModel):
    """
    Unified batch indicator response.
    Each key in 'results' maps to the indicator type requested.
    """
    status: str = "success"
    symbol: str
    timeframe: str
    data_source: str
    batch_latency_ms: float
    results: Dict[str, DetailedIndicatorResponse]

# Legacy single-indicator request (kept for backward compat with /calculate/* endpoints)
class BaseIndicatorRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "H1"
    fund_id: Optional[str] = None
    params: Dict[str, Any] = {}

    @validator('symbol')
    def validate_symbol_iso(cls, v):
        # Allow common indices (VIX, DXY, US10Y)
        if v in ["VIX", "DXY", "US10Y", "US02Y", "SPX500", "NAS100"]:
            return v
        v = v.upper().replace("/", "").replace("_", "")
        if not re.match(r"^[A-Z]{3,8}$", v):
            raise ValueError("Symbol must be valid uppercase ISO (e.g. EURUSD) or known index.")
        return v

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
    symbol: str
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: Optional[List[float]] = None
    timestamps: Optional[List[str]] = None
    # For Correlation analysis
    second_close: Optional[List[float]] = None
    second_symbol: Optional[str] = None
    timeframe: Optional[str] = "H1"
    # For Positioning analysis
    oi_call: Optional[List[float]] = None
    oi_put: Optional[List[float]] = None
    oi_strikes: Optional[List[float]] = None

class SMCResponse(BaseModel):
    order_blocks: List[Dict[str, Any]]
    fvgs: List[Dict[str, Any]]
    liquidity_sweeps: List[Dict[str, Any]] = []
    structure: Dict[str, Any] = {}
    setups: List[Dict[str, Any]] = []
    auto_fibs: Dict[str, float] = {}
    institutional_bias: str = "NEUTRAL"
    strategic_reasoning: str = ""
    timestamp: Optional[datetime] = None  # Analysis snapshot time
    timeframe: Optional[str] = "H1"
    meta: Dict[str, Any] = {}  # Global confluence or strength metrics

class SMCBatchRequest(BaseModel):
    # Dictionary mapping symbol -> SMCRequest
    requests: Dict[str, SMCRequest]

class SMCBatchResponse(BaseModel):
    # Map symbol -> SMCResponse
    results: Dict[str, SMCResponse]

class SMCChecklistItem(BaseModel):
    status: bool
    value: str
    comment: str

class SMCVisuals(BaseModel):
    poi_zone: Optional[Dict[str, float]] = None
    trigger_level: float
    stop_loss: float
    take_profit: float
    timeframes: Optional[Dict[str, str]] = None

class SMCDebugInfo(BaseModel):
    last_candle_ts: datetime
    processing_ms: float
    data_source: str

class SMCMTFResponse(BaseModel):
    summary: str
    confluence_score: int
    is_case_b: bool
    bias: str
    checklist: Dict[str, SMCChecklistItem]
    scenario_analysis: List[str] = []
    visuals: SMCVisuals
    metrics: Optional[Dict[str, Any]] = None
    debug_info: SMCDebugInfo

class SMCMTFRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframes: List[str] = ["H4", "H1", "M15"]
    fund_id: Optional[str] = None
    # Optional override: candles[symbol][timeframe] = List of Candle Dicts
    candles: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]] = None


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
    fees: float = 0.0001
    slippage: float = 0.0001
    size: float = 1.0
    size_type: str = 'amount'
    strategy_id: Optional[str] = None
    fund_id: Optional[str] = None
    trading_config_id: Optional[str] = None
    optimization: Optional[OptimizationConfig] = None

class StrategyBacktestRequest(BaseModel):
    code: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    fees: float = 0.0001
    slippage: float = 0.0001
    size: float = 1.0
    size_type: str = 'amount'
    optimization: Optional[OptimizationConfig] = None
    strategy_id: Optional[str] = None

class TradeResult(BaseModel):
    entry_time: datetime
    exit_time: datetime
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percent: float
    size: float = 0.0

class BacktestMetrics(BaseModel):
    total_return: float
    total_return_percent: float
    max_drawdown: float
    max_drawdown_percent: float
    win_rate: float
    benchmark_return: float = 0.0
    sharpe_ratio: Optional[float] = 0.0
    total_trades: int
    winning_trades: int
    losing_trades: int
    candle_count: Optional[int] = 0

    # CFA / Advanced Metrics (Olympus Upgrade)
    sortino_ratio: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0

    # Radar Chart Metrics
    profit_factor: float = 0.0
    k_ratio: float = 0.0
    volatility: float = 0.0
    kurtosis: float = 0.0
    reward_to_risk_ratio: float = 0.0

class BacktestResponse(BaseModel):
    id: str
    status: str
    metrics: Optional[BacktestMetrics] = None
    trades: List[TradeResult] = []
    equity_curve: List[EquityPoint] = []
    best_params: Optional[Dict[str, Any]] = None
    plot_json: Optional[str] = None
class SensitivityMetrics(BaseModel):
    p95: float
    median: float
    worst: Optional[float] = None
    best: Optional[float] = None

class MonteCarloResponse(BaseModel):
    iterations: int
    max_drawdown: SensitivityMetrics
    total_return: SensitivityMetrics
    sharpe_ratio: SensitivityMetrics
    ruin_probability: float
    equity_curves: Optional[List[List[float]]] = None

class MonteCarloRequest(BaseModel):
    trades: List[Dict[str, Any]]
    iterations: int = 1000
    strategy_id: Optional[str] = None

class OptimizationResult(BaseModel):
    params: Dict[str, Any]
    metrics: Dict[str, float]

class OptimizationResponse(BaseModel):
    results: List[OptimizationResult]

class FoundryAssembleRequest(BaseModel):
    config: Dict[str, Any]

class FoundryAssembleResponse(BaseModel):
    pipeline_hash: str
    errors: List[str]

class WalkForwardRequest(BaseModel):
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    config: Dict[str, Any] # Foundry Config with Optimization Params

class WalkForwardResponse(BaseModel):
    robustness_score: int
    avg_sharpe_test: float
    details: List[Dict[str, Any]]

# ==========================
# Quant Layer Schemas
# ==========================

class QuantAnalyzeRequest(BaseModel):
    symbol: str
    timeframe: str = "H1"
    limit: int = 1000
    fund_id: Optional[str] = None

class QuantSizingRequest(BaseModel):
    symbol: str
    entry_price: float
    stop_loss: float
    equity: float
    strategy_id: Optional[str] = None
    timeframe: str = "H1"
    limit: int = 1000
    fund_id: Optional[str] = None

class QuantAnalyzeResponse(BaseModel):
    symbol: str
    timeframe: str
    price: float
    composite_risk_score: float
    edge_score: float
    layers: Dict[str, Any]
    context: Dict[str, Any]
    timestamp: datetime

class QuantSizingResponse(BaseModel):
    risk_map: QuantAnalyzeResponse
    sizing: Dict[str, Any]

# --- New Quant Analytics Response Schemas ---

class VolatilityMetrics(BaseModel):
    realized_vol: float
    parkinson_vol: float
    yang_zhang_vol: float
    rolling_vol_series: List[float]

class VaRMetrics(BaseModel):
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float

class FactorExposures(BaseModel):
    beta: float
    momentum: float
    rsi: float
    volatility_regime: str

class DrawdownMetrics(BaseModel):
    max_drawdown: float
    current_drawdown: float
    dd_duration: int
    recovery_factor: float

class APIResponse_VolatilityMetrics(BaseModel):
    status: str
    data: VolatilityMetrics
    timestamp: datetime

class APIResponse_VaRMetrics(BaseModel):
    status: str
    data: VaRMetrics
    timestamp: datetime

class APIResponse_FactorExposures(BaseModel):
    status: str
    data: FactorExposures
    timestamp: datetime

class APIResponse_DrawdownMetrics(BaseModel):
    status: str
    data: DrawdownMetrics
    timestamp: datetime

# Backward Compatibility Aliases
IndicatorRequest = BaseIndicatorRequest
IndicatorResponse = DetailedIndicatorResponse
IndicatorResponse = DetailedIndicatorResponse
ATRRequest = BaseIndicatorRequest
RSIRequest = BaseIndicatorRequest
MACDRequest = BaseIndicatorRequest
BBandsRequest = BaseIndicatorRequest
MACDResponse = DetailedIndicatorResponse
BBandsResponse = DetailedIndicatorResponse
