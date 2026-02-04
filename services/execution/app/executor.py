### services/execution/app/executor.py
# Execution guardrails

from decimal import Decimal, ROUND_DOWN
from pydantic import BaseModel, Field
from typing import Optional
from app.services.minimax_service import MinimaxService

class ExecutionRequest(BaseModel):
    risk_usd: Decimal = Field(..., description="Maximum risk in USD")
    sl_distance_usd: Decimal = Field(..., description="Distance to SL in USD")
    min_lot: Decimal = Field(..., description="Minimum lot size")
    
    # Minimax Inputs
    reward_usd: Optional[Decimal] = Field(None, description="Potential reward in USD")
    confidence: float = Field(0.8, description="Signal confidence")
    pain_threshold: float = Field(50.0, description="Pain threshold in USD")

    # TCA / Market Impact Inputs
    daily_volume: Optional[float] = Field(None, description="Average Daily Volume (Units)")
    volatility: Optional[float] = Field(None, description="Daily Volatility (Decimal, e.g. 0.01)")
    max_slippage: float = Field(0.001, description="Max allowed price impact (0.1%)")

class ExecutionResult(BaseModel):
    can_execute: bool
    lot: Decimal
    reason: str
    estimated_impact: float = 0.0

def calculate_market_impact(lot_size: float, daily_volume: float, volatility: float) -> float:
    """
    Estimates price impact using the Square-Root Law.
    Impact ~ Volatility * sqrt(Size / Volume)
    """
    if daily_volume <= 0:
        return 0.0
    
    participation_rate = lot_size / daily_volume
    # Constant 'c' is often estimated between 0.1 and 1.0 depending on the asset class.
    # We assume c=1.0 for conservative estimation.
    impact = volatility * (participation_rate ** 0.5)
    return float(impact)

def can_execute(req: ExecutionRequest) -> ExecutionResult:
    """
    Calculates position size and validates against risk constraints and market impact.
    """
    if req.sl_distance_usd <= 0:
        return ExecutionResult(
            can_execute=False,
            lot=Decimal("0.00"),
            reason="Stop loss distance must be positive"
        )

    # Calculate raw lot size
    raw_lot = req.risk_usd / req.sl_distance_usd
    
    # Round down to 2 decimal places (floor)
    lot = raw_lot.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    if lot < req.min_lot:
        return ExecutionResult(
            can_execute=False,
            lot=lot,
            reason=f"Calculated lot {lot} is below minimum {req.min_lot}"
        )

    # TCA: Market Impact Check
    estimated_impact = 0.0
    if req.daily_volume and req.volatility:
        estimated_impact = calculate_market_impact(
            float(lot), 
            req.daily_volume, 
            req.volatility
        )
        
        if estimated_impact > req.max_slippage:
            return ExecutionResult(
                can_execute=False,
                lot=lot,
                reason=f"Market Impact ({estimated_impact:.4%}) exceeds tolerance ({req.max_slippage:.4%})",
                estimated_impact=estimated_impact
            )

    # Minimax Check
    if req.reward_usd is not None:
        risk_f = float(req.risk_usd)
        reward_f = float(req.reward_usd)
        
        is_safe, regret, reason = MinimaxService.calculate_regret(
            risk_usd=risk_f,
            reward_usd=reward_f,
            confidence=req.confidence,
            pain_threshold=req.pain_threshold
        )
        
        if not is_safe:
             return ExecutionResult(
                can_execute=False,
                lot=lot,
                reason=f"Minimax: {reason}",
                estimated_impact=estimated_impact
            )

    return ExecutionResult(
        can_execute=True,
        lot=lot,
        reason="ok",
        estimated_impact=estimated_impact
    )
