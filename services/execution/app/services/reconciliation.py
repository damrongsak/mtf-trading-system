import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.models import Trade, TradeStatus

logger = logging.getLogger(__name__)

class ReconciliationService:
    @staticmethod
    async def reconcile_parent_fill(db: AsyncSession, parent_id: UUID):
        """
        Calculates aggregate fill for a parent trade and updates its status.
        """
        try:
            # 1. Fetch Parent Trade
            res = await db.execute(select(Trade).where(Trade.trade_id == parent_id))
            parent = res.scalar_one_or_none()
            
            if not parent:
                logger.warning(f"🏛️ [Reconciliation] Parent trade {parent_id} not found.")
                return

            # 2. Calculate aggregate filled units from children
            # Note: Child trades are those with parent_trade_id == parent_id
            # We assume child trades are only those that reached 'OPEN' (filled)
            # or we can filter by status.
            res = await db.execute(
                select(func.sum(Trade.lot_size * 100000.0))
                .where(Trade.parent_trade_id == parent_id)
                # .where(Trade.status == TradeStatus.OPEN) # If status is OPEN, it means filled
            )
            total_filled_units = res.scalar() or 0.0
            
            # 3. Determine New Status
            # We use parent.lot_size * 100000.0 as the target units
            target_units = parent.lot_size * 100000.0
            
            old_status = parent.algo_status
            new_status = old_status
            
            if total_filled_units >= target_units:
                new_status = "FILLED"
            elif total_filled_units > 0:
                new_status = "FILLED_PARTIAL"
            
            # 4. Update Parent
            if not parent.metadata_json:
                parent.metadata_json = {}
            
            parent.metadata_json["filled_units"] = total_filled_units
            parent.metadata_json["target_units"] = target_units
            parent.algo_status = new_status
            
            await db.commit()
            
            if old_status != new_status:
                logger.info(f"🏛️ [Reconciliation] Parent {parent_id} status updated: {old_status} -> {new_status} ({total_filled_units}/{target_units} units)")
            else:
                logger.info(f"🏛️ [Reconciliation] Parent {parent_id} progress: {total_filled_units}/{target_units} units")

        except Exception as e:
            logger.error(f"🏛️ [Reconciliation] Error for parent {parent_id}: {e}", exc_info=True)
            raise e
