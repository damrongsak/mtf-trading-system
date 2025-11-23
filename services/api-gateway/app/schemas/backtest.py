from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    strategy_params: Dict[str, Any] = {}
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0

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
    total_trades: int
    winning_trades: int
    losing_trades: int

class BacktestResponse(BaseModel):
    id: str
    status: str
    metrics: Optional[BacktestMetrics] = None
    trades: List[TradeResult] = []
