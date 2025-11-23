"""
MTF Trading System - Pydantic Schemas

All Pydantic schemas for API request/response validation.
Derived from specs/01_data_model.yaml
"""

from app.schemas.candle import (
    CandleBase,
    CandleCreate,
    CandleUpdate,
    CandleResponse
)

from app.schemas.trade import (
    TradeBase,
    TradeCreate,
    TradeUpdate,
    TradeResponse,
    TradeStatus,
    TradeDirection,
    RiskCheckRequest,
    RiskCheckResponse
)

from app.schemas.strategy_run import (
    StrategyRunBase,
    StrategyRunCreate,
    StrategyRunUpdate,
    StrategyRunResponse,
    RunStatus,
    BacktestScorecard
)

from app.schemas.risk_rule import (
    RiskRuleBase,
    RiskRuleCreate,
    RiskRuleUpdate,
    RiskRuleResponse,
    RiskRuleResponse,
    RuleType
)

from app.schemas.signal import (
    SignalRequest,
    SignalResponse
)

__all__ = [
    # Candle schemas
    "CandleBase",
    "CandleCreate",
    "CandleUpdate",
    "CandleResponse",

    # Trade schemas
    "TradeBase",
    "TradeCreate",
    "TradeUpdate",
    "TradeResponse",
    "TradeStatus",
    "TradeDirection",
    "RiskCheckRequest",
    "RiskCheckResponse",

    # Strategy Run schemas
    "StrategyRunBase",
    "StrategyRunCreate",
    "StrategyRunUpdate",
    "StrategyRunResponse",
    "RunStatus",
    "BacktestScorecard",

    # Risk Rule schemas
    "RiskRuleBase",
    "RiskRuleCreate",
    "RiskRuleUpdate",
    "RiskRuleResponse",
    "RuleType",

    # Signal schemas
    "SignalRequest",
    "SignalResponse",
]
