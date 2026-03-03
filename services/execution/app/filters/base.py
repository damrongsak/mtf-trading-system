from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Fund, RiskFilter

class BaseFilter:
    """
    Base class for Layer 4 Modular Risk Filters.
    """
    def __init__(self, filter_type: str):
        self.filter_type = filter_type

    async def validate(
        self,
        db: AsyncSession,
        adapter: Any,
        fund: Fund,
        symbol: str,
        direction: str,
        sl_price: float,
        tp_price: float,
        entry_price: float,
        filter_config: RiskFilter
    ) -> bool:
        """
        Validate the order against the specific filter constraint.
        Should return True if valid, or raise ValueError if restricted.
        """
        raise NotImplementedError("Subclasses must implement validate()")
