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
    
    # Minimax Inputs (Optional for backward compatibility)
    reward_usd: Optional[Decimal] = Field(None, description="Potential reward in USD")
    confidence: float = Field(0.8, description="Signal confidence")
    pain_threshold: float = Field(50.0, description="Pain threshold in USD")

class ExecutionResult(BaseModel):
    can_execute: bool
    lot: Decimal
    reason: str

def can_execute(req: ExecutionRequest) -> ExecutionResult:
    """
    Calculates position size and validates against risk constraints.
    
    Logic:
    1. Calculate lot = risk_usd / sl_distance_usd
    2. Round down to 2 decimal places (standard lot step, assuming 0.01 step)
    3. Check if lot >= min_lot
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
    # quantize with ROUND_DOWN to ensure we don't exceed risk due to rounding up
    lot = raw_lot.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    if lot < req.min_lot:
        return ExecutionResult(
            can_execute=False,
            lot=lot,
            reason=f"Calculated lot {lot} is below minimum {req.min_lot}"
        )

    # Minimax Check
    if req.reward_usd is not None:
        # Convert Decimals to float for MinimaxService (it uses floats)
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
                reason=f"Minimax: {reason}"
            )

    return ExecutionResult(
        can_execute=True,
        lot=lot,
        reason="ok"
    )
