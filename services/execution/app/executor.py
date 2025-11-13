### services/execution/app/executor.py
# Execution guardrails

def can_execute(
    risk_usd: float, sl_distance_usd: float, min_lot: float
) -> bool:
    lot = risk_usd / sl_distance_usd if sl_distance_usd > 0 else 0
    return lot >= min_lot
