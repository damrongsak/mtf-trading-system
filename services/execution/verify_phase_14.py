import asyncio
import json
import logging
import uuid
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock database before imports to avoid connection attempts
import sys
from app.models import Trade, TradeStatus

async def test_reconciliation_logic():
    """
    Simulates the filling of child trades and verifies that the parent status
    progresses from RUNNING -> FILLED_PARTIAL -> FILLED.
    """
    from app.services.reconciliation import ReconciliationService
    
    parent_id = uuid.uuid4()
    # Parent: 100,000 units (1.0 lot)
    parent_trade = Trade(
        trade_id=parent_id,
        lot_size=1.0,
        algo_status="RUNNING",
        metadata_json={}
    )
    
    # Mock DB behavior
    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        # Check if it's a select for parent
        if "where trades.trade_id =" in stmt_str:
            return MagicMock(scalar_one_or_none=lambda: parent_trade)
        
        # Check if it's a sum for children
        if "sum" in stmt_str and "parent_trade_id" in stmt_str:
            return MagicMock(scalar=lambda: db.current_sum)
        
        return MagicMock()

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=mock_execute)
    db.current_sum = 0.0
    
    logger.info("--- Starting Reconciliation Test ---")
    
    # 1. First slice filled (25,000 units)
    logger.info("Scenario 1: First child filled (25k units)")
    db.current_sum = 25000.0
    await ReconciliationService.reconcile_parent_fill(db, parent_id)
    
    logger.info(f"Parent Status: {parent_trade.algo_status}")
    assert parent_trade.algo_status == "FILLED_PARTIAL"
    assert parent_trade.metadata_json["filled_units"] == 25000.0
    
    # 2. More slices filled (Total 75,000 units)
    logger.info("Scenario 2: More children filled (Total 75k units)")
    db.current_sum = 75000.0
    await ReconciliationService.reconcile_parent_fill(db, parent_id)
    
    logger.info(f"Parent Status: {parent_trade.algo_status}")
    assert parent_trade.algo_status == "FILLED_PARTIAL"
    
    # 3. Last slice filled (Total 100,000 units)
    logger.info("Scenario 3: Final child filled (Total 100k units)")
    db.current_sum = 100000.0
    await ReconciliationService.reconcile_parent_fill(db, parent_id)
    
    logger.info(f"Parent Status: {parent_trade.algo_status}")
    assert parent_trade.algo_status == "FILLED"
    assert parent_trade.metadata_json["filled_units"] == 100000.0

    logger.info("✅ Phase 14 Logic Verification Successful!")

if __name__ == "__main__":
    # Ensure app.database doesn't try to connect
    with patch("app.database.AsyncSessionLocal", new=MagicMock()):
        asyncio.run(test_reconciliation_logic())
