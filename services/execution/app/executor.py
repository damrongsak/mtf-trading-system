### services/execution/app/executor.py
# Execution guardrails

from decimal import Decimal, ROUND_DOWN
from pydantic import BaseModel, Field

class ExecutionRequest(BaseModel):
    risk_usd: Decimal = Field(..., description="Maximum risk in USD")
    sl_distance_usd: Decimal = Field(..., description="Distance to SL in USD")
    min_lot: Decimal = Field(..., description="Minimum lot size")

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

    return ExecutionResult(
        can_execute=True,
        lot=lot,
        reason="ok"
    )
