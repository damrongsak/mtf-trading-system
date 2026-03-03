from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Fund, RiskFilter
from app.filters.base import BaseFilter
import logging

logger = logging.getLogger(__name__)

class SpreadFilter(BaseFilter):
    def __init__(self):
        super().__init__("SPREAD_FILTER")

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
        max_spread_pips = filter_config.threshold_parameters.get("max_spread_pips", 3.0)
        
        try:
             # Fast quote from adapter (often cached or streaming)
             quote = await adapter.get_quote(symbol)
             if not quote:
                 logger.warning(f"SpreadFilter: No quote available for {symbol}, passing by default")
                 return True
                 
             ask = quote["ask"]
             bid = quote["bid"]
             spread = ask - bid
             
             pip_size = 0.1 if "XAU" in symbol else 0.0001
             spread_pips = spread / pip_size
             
             if spread_pips > max_spread_pips:
                 raise ValueError(f"Risk Violation: Spread too high ({spread_pips:.1f} > {max_spread_pips} pips)")
                 
        except AttributeError:
             # Adapter missing get_quote
             logger.warning(f"SpreadFilter: Adapter missing get_quote() for {symbol}")
        except Exception as e:
             if isinstance(e, ValueError): raise e
             logger.warning(f"SpreadFilter error: {e}")
             
        return True
