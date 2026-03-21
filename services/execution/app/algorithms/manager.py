import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Trade, TradeStatus, TradeDirection
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class AlgoManager:
    """
    Orchestrates Institutional Execution Algorithms (Phase 12).
    Generates and schedules child orders (slices) for a parent trade.
    """

    @staticmethod
    async def create_algo_trade(req_data: dict, db: AsyncSession) -> dict:
        """
        Entry point for Algorithmic Orders.
        Creates a 'Parent' trade record and triggers the slicing logic.
        """
        algo_name = req_data.get("execution_algo", "TWAP").upper()
        algo_params = req_data.get("algo_params", {})
        
        # 1. Create Parent Trade Record (Status: PENDING)
        parent_id = uuid.uuid4()
        
        # We need to calculate the total units now or let the algo do it.
        # For TWAP, we calculate total units from risk/sl as usual.
        from app.services.order_service import OrderService
        # ... logic to calculate total units ...
        # (Actually, execute_smart_order already calculated 'units' and 'target_risk')
        # We'll expect them in the req_data from OrderService
        
        total_units = req_data.get("units", 0.0)
        total_risk = req_data.get("risk_usd", 0.0)
        
        parent_trade = Trade(
            trade_id=parent_id,
            broker_account_id=uuid.UUID(req_data["broker_account_id"]),
            symbol=req_data["symbol"],
            strategy_name=req_data["generated_by"],
            signal_timestamp=datetime.utcnow(),
            status=TradeStatus.PENDING,
            direction=TradeDirection.LONG if req_data["direction"] == "BULLISH" else TradeDirection.SHORT,
            entry_price=req_data.get("entry_price", 0.0),
            sl_price=req_data.get("stop_loss", 0.0),
            tp_price=req_data.get("take_profit", 0.0),
            lot_size=total_units / 100000.0, # Standardized
            risk_usd=total_risk,
            execution_algo=algo_name,
            algo_params=algo_params,
            algo_status="RUNNING",
            metadata_json={"is_parent": True}
        )
        
        db.add(parent_trade)
        await db.commit()
        
        logger.info(f"🏛️ [AlgoManager] Created Parent Trade {parent_id} for {algo_name}")
        
        # 2. Trigger Slicing Logic via Redis
        rc = get_redis_client()
        algo_command = {
            "type": "ALGO_START",
            "parent_trade_id": str(parent_id),
            "algo_name": algo_name,
            "params": algo_params,
            "req_data": req_data # Original request data for slices
        }
        
        await rc.lpush("queue:execution:algo", json.dumps(algo_command))
        
        return {
            "id": str(parent_id),
            "status": "ALGO_STARTED",
            "algo": algo_name,
            "trace_id": req_data.get("client_order_id")
        }

    @staticmethod
    async def process_algo_step(rc: Any, db: AsyncSession, command: dict):
        """
        Background step: Generates the next slice for an active algo trade.
        """
        parent_id = command.get("parent_trade_id")
        algo_name = command.get("algo_name")
        req_data = command.get("req_data")
        
        # For Phase 12.1: Simple TWAP implementation
        from app.algorithms.twap import TwapAlgorithm
        if algo_name == "TWAP":
            await TwapAlgorithm.execute(rc, db, parent_id, req_data)
        else:
            logger.error(f"Unsupported algorithm: {algo_name}")
