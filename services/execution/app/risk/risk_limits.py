import logging
from datetime import datetime, timezone
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from typing import Optional

from app.models import Trade, TradeStatus, Fund, RiskFilter

logger = logging.getLogger(__name__)

class RiskLimitsAgent:
    """
    Agent responsible for Account and Fund level limits (Phase 3).
    - Daily Drawdown
    - Max Trades Per Day
    - Consecutive Losses
    """
    
    @staticmethod
    async def check_limits(db: AsyncSession, fund: Fund, broker_account_id: str):
        """
        Validates the overall risk state before allowing a new trade.
        """
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        try:
            account_uuid = uuid.UUID(broker_account_id)
        except (ValueError, TypeError):
            logger.warning(f"RiskLimitsAgent: Invalid broker_account_id {broker_account_id}")
            return True
            
        # --- 1. Daily Drawdown Limit ---
        # Calculate PnL for today for this specific account
        active_trades_query = await db.execute(
            select(func.sum(Trade.pnl_usd))
            .where(Trade.broker_account_id == account_uuid)
            .where(Trade.status == TradeStatus.CLOSED)
            .where(Trade.exit_timestamp >= today_start)
        )
        daily_pnl = active_trades_query.scalar() or 0.0
        
        if fund.max_drawdown_threshold and daily_pnl < -(fund.max_drawdown_threshold):
            raise ValueError(f"Risk Violation: Daily Drawdown Limit Reached (${abs(daily_pnl):.2f})")

        # --- 2. Dynamic Configurations (RiskFilter) ---
        # Fetch limits for this specific fund or account
        stmt = select(RiskFilter).where(RiskFilter.is_enabled == True).where(
            RiskFilter.filter_type.in_(["MAX_TRADES_PER_DAY", "CONSECUTIVE_LOSSES"])
        )
        result = await db.execute(stmt)
        limits_configs = result.scalars().all()
        
        # Apply limits if configured
        for config in limits_configs:
            # We only enforce if the target matches SYSTEM, this FUND, or this ACCOUNT
            target_match = (
                config.target_type == "SYSTEM" or
                (config.target_type == "FUND" and config.target_id == fund.id) or
                (config.target_type == "BROKER_ACCOUNT" and config.target_id == account_uuid)
            )
            if not target_match:
                continue
                
            if config.filter_type == "MAX_TRADES_PER_DAY":
                max_trades = config.threshold_parameters.get("max_trades", 10)
                
                trades_today_query = await db.execute(
                    select(func.count(Trade.trade_id))
                    .where(Trade.broker_account_id == account_uuid)
                    .where(Trade.signal_timestamp >= today_start)
                )
                trades_today = trades_today_query.scalar() or 0
                
                if trades_today >= max_trades:
                    raise ValueError(f"Risk Violation: Max Trades Per Day Reached ({trades_today} >= {max_trades})")
                    
            elif config.filter_type == "CONSECUTIVE_LOSSES":
                max_losses = config.threshold_parameters.get("max_consecutive_losses", 3)
                
                # Fetch recent closed trades
                recent_trades_query = await db.execute(
                    select(Trade)
                    .where(Trade.broker_account_id == account_uuid)
                    .where(Trade.status == TradeStatus.CLOSED)
                    .order_by(Trade.exit_timestamp.desc())
                    .limit(max_losses)
                )
                recent_trades = recent_trades_query.scalars().all()
                
                if len(recent_trades) == max_losses:
                    # Check if all of them are losses
                    all_lost = all(t.pnl_usd is not None and t.pnl_usd < 0 for t in recent_trades)
                    if all_lost:
                        raise ValueError(f"Risk Violation: Consecutive Losses Limit Reached ({max_losses} losses)")

        return True
