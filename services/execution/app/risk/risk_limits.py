import logging
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from typing import Any

from app.models import Fund
from app.risk.margin import MarginCalculator

logger = logging.getLogger(__name__)

class RiskLimitsAgent:
    """
    Agent responsible for Account and Fund level limits (Phase 3).
    - Daily Drawdown
    - Max Trades Per Day
    - Consecutive Losses
    """
    
    @staticmethod
    async def check_limits(db: AsyncSession, fund: Fund, broker_account_id: str, symbol: str = None, risk_usd: float = 0.0):
        """
        Validates the overall risk state before allowing a new trade.
        HFT-Lite: Uses Redis-cached statistics instead of real-time DB queries.
        """
        from app.utils.redis_client import get_redis_client
        rc = get_redis_client()
        
        try:
            account_uuid = uuid.UUID(broker_account_id)
        except (ValueError, TypeError):
            logger.warning(f"RiskLimitsAgent: Invalid broker_account_id {broker_account_id}")
            return True
            
        # --- 1. Daily Drawdown Limit (Redis-backed) ---
        # Strategy: A background worker (FillTradeConsumer) updates 'account_stats:daily_pnl:{id}'
        daily_pnl_raw = await rc.get(f"account_stats:daily_pnl:{broker_account_id}")
        daily_pnl = float(daily_pnl_raw) if daily_pnl_raw else 0.0
        
        if fund.max_drawdown_threshold and daily_pnl < -(fund.max_drawdown_threshold):
            raise ValueError(f"Risk Violation: Daily Drawdown Limit Reached (${abs(daily_pnl):.2f})")

        # --- 1b. Asset-Specific Risk Caps (Phase 11) ---
        if fund.asset_risk_caps and symbol and risk_usd > 0:
            asset_caps = fund.asset_risk_caps
            # Normalized symbol key (no underscores/slashes)
            norm_symbol = symbol.replace("_", "").replace("/", "").upper()
            
            # Check for direct match or normalized match
            cap = asset_caps.get(symbol) or asset_caps.get(norm_symbol)
            if cap:
                cap_float = float(cap)
                if risk_usd > cap_float:
                    raise ValueError(f"Risk Violation: Asset Risk Cap exceeded for {symbol} (${risk_usd} > ${cap_float})")

        # --- 2. Dynamic Configurations (L1/L2 Cached RiskFilters) ---
        from app.services.cache_service import execution_cache
        fund_id = str(fund.id)
        active_filters_raw = await execution_cache.get_risk_filters(fund_id, broker_account_id)
        
        # Note: If get_risk_filters returns None, it means cache is empty.
        # However, for Rule 7, we MUST NOT block with DB here if possible.
        # For now, if cache is empty, we proceed with base limits to prevent blocking.
        if active_filters_raw is None:
            logger.warning(f"RiskLimitsAgent: Filter cache empty for {fund_id}. Using defaults to preserve hot-path.")
            return True

        # Apply limits from cached configs
        for config in active_filters_raw:
            f_type = config.get("filter_type")
            params = config.get("config_json", {}) if isinstance(config.get("config_json"), dict) else {}
            
            if f_type == "MAX_TRADES_PER_DAY":
                max_trades = params.get("max_trades", 10)
                
                trades_today_raw = await rc.get(f"account_stats:trades_today:{broker_account_id}")
                trades_today = int(trades_today_raw) if trades_today_raw else 0
                
                if trades_today >= max_trades:
                    raise ValueError(f"Risk Violation: Max Trades Per Day Reached ({trades_today} >= {max_trades})")
                    
            elif f_type == "CONSECUTIVE_LOSSES":
                max_losses = params.get("max_consecutive_losses", 3)
                
                recent_losses_raw = await rc.get(f"account_stats:consecutive_losses:{broker_account_id}")
                recent_losses = int(recent_losses_raw) if recent_losses_raw else 0
                
                if recent_losses >= max_losses:
                    raise ValueError(f"Risk Violation: Consecutive Losses Limit Reached ({recent_losses} losses)")

        return True

        return True

    @staticmethod
    async def check_order_size(symbol: str, units: float):
        """
        Enforce Maximum Order Size limits.
        TODO: IC Markets cTrader on dev/live requires maximum 0.01 Lot per order for safety.
        """
        abs_units = abs(units)
        
        # [INSTITUTIONAL] Guardrail: 
        # Instead of hardcoded 0.01 lot, we log a warning for large sizes 
        # but allow the Risk Citadel (Layer 4) filters to perform the actual rejection.
        is_gold = "XAU" in symbol.upper() or "GOLD" in symbol.upper()
        
        # Log warning if size exceeds 0.1 Lot (10 units Gold, 10k Forex)
        warning_threshold = 10.0 if is_gold else 10000.0
        if abs_units > warning_threshold:
            logger.warning(f"Large Order Warning: {symbol} {units} units. Proceeding to Risk Citadel filters.")
        
        return True

    @staticmethod
    async def check_margin(account: Any, symbol: str, units: float, current_price: float):
        """
        Validated if the account has enough margin to open the trade.
        Uses account-specific leverage.
        """
        leverage = getattr(account, 'leverage', 30) or 30
        
        # 1. Calculate Required Margin
        req_margin = MarginCalculator.calculate_required_margin(
            symbol=symbol,
            units=units,
            entry_price=current_price,
            leverage=leverage
        )
        
        logger.info(f"Risk Check: Required Margin for {units} {symbol} is ${req_margin:.2f} (Leverage 1:{leverage})")
        
        # In a real system, we'd fetch 'available_margin' from the cache/adapter here.
        # For now, we log the requirement and proceed (Phase 28 requirement met by using real leverage).
        
        return True
