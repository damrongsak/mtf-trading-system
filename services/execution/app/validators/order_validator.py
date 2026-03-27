import logging
from typing import List
from app.models import RiskFilter

logger = logging.getLogger(__name__)

class OrderValidator:
    """
    Validates core order parameters before execution.
    Implements Phase 1 rules: SL/TP Mandatory, SL Distance, RR Ratio.
    """
    @classmethod
    def validate(cls, 
                 symbol: str, 
                 entry_price: float, 
                 sl_price: float, 
                 tp_price: float, 
                 side: str, 
                 order_type: str, 
                 current_ask: float = None, 
                 current_bid: float = None, 
                 active_filters: List[RiskFilter] = None):
        """
        Runs validation against a list of active RiskFilters and logical trading rules.
        """
        # Defensive Handling
        side = (side or "BUY").upper()
        order_type = (order_type or "MARKET").upper()
        entry_price = float(entry_price or 0.0)
        sl_price = float(sl_price or 0.0)
        tp_price = float(tp_price or 0.0)
        is_buy = side in ["BUY", "LONG"]
        
        # 1. Logical Directional Integrity (Fundamental Trading Rules)
        if sl_price > 0:
            if is_buy and sl_price >= entry_price:
                raise ValueError(f"Invalid SL: For BUY orders, SL ({sl_price}) must be below Entry ({entry_price})")
            if not is_buy and sl_price <= entry_price:
                raise ValueError(f"Invalid SL: For SELL orders, SL ({sl_price}) must be above Entry ({entry_price})")
        
        if tp_price > 0:
            if is_buy and tp_price <= entry_price:
                raise ValueError(f"Invalid TP: For BUY orders, TP ({tp_price}) must be above Entry ({entry_price})")
            if not is_buy and tp_price >= entry_price:
                raise ValueError(f"Invalid TP: For SELL orders, TP ({tp_price}) must be below Entry ({entry_price})")

        # 2. Order Type vs Market Price (Pending Order Logic)
        if order_type in ["LIMIT", "STOP", "STOP_LIMIT"]:
            price_to_check = current_ask if is_buy else current_bid
            if price_to_check:
                if order_type == "LIMIT":
                    if is_buy and entry_price >= price_to_check:
                        raise ValueError(f"Invalid BUY LIMIT: Price ({entry_price}) must be below Current ASK ({price_to_check})")
                    if not is_buy and entry_price <= price_to_check:
                        raise ValueError(f"Invalid SELL LIMIT: Price ({entry_price}) must be above Current BID ({price_to_check})")
                elif order_type == "STOP":
                    if is_buy and entry_price <= price_to_check:
                        raise ValueError(f"Invalid BUY STOP: Price ({entry_price}) must be above Current ASK ({price_to_check})")
                    if not is_buy and entry_price >= price_to_check:
                        raise ValueError(f"Invalid SELL STOP: Price ({entry_price}) must be below Current BID ({price_to_check})")

        # 3. Dynamic Risk Filters (Configurable Rules)
        if active_filters:
            for f in active_filters:
                if not f.is_enabled:
                    continue

                if f.filter_type == "SL_MANDATORY":
                    if not sl_price or sl_price <= 0:
                        raise ValueError("Risk Violation: Stop Loss is mandatory")

                elif f.filter_type == "TP_MANDATORY":
                    if not tp_price or tp_price <= 0:
                        raise ValueError("Risk Violation: Take Profit is mandatory")

                elif f.filter_type == "SL_DISTANCE":
                    if sl_price and sl_price > 0 and entry_price and entry_price > 0:
                        min_pip_distance = f.threshold_parameters.get("min_pip_distance", 0)
                        if min_pip_distance > 0:
                            dist = abs(entry_price - sl_price)
                            # Assume 1 pip = 0.1 for XAU, 0.0001 for FX
                            pip_size = 0.1 if "XAU" in symbol else 0.0001
                            pips = dist / pip_size
                            if pips < min_pip_distance:
                                raise ValueError(f"Risk Violation: SL Distance too small ({pips:.1f} < {min_pip_distance} pips)")

                elif f.filter_type == "RR_RATIO":
                    if sl_price and sl_price > 0 and tp_price and tp_price > 0 and entry_price and entry_price > 0:
                        min_ratio = f.threshold_parameters.get("min_ratio", 0)
                        if min_ratio > 0:
                            risk = abs(entry_price - sl_price)
                            reward = abs(tp_price - entry_price)
                            if risk > 0:
                                rr = reward / risk
                                if rr < min_ratio:
                                    raise ValueError(f"Risk Violation: RR Ratio too low ({rr:.2f} < {min_ratio})")

        return True
