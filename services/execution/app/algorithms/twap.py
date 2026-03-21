import logging
import asyncio
import json
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class TwapAlgorithm:
    """
    Time-Weighted Average Price Algorithm (Phase 12.1).
    Splits an order into $N$ equal parts over $T$ duration.
    """

    @staticmethod
    async def execute(rc: Any, db: AsyncSession, parent_id: str, req_data: dict):
        """
        Takes the parent request and schedules the first slice, then 
        schedules next slices with Redis delays.
        """
        params = req_data.get("algo_params", {})
        duration_sec = int(params.get("duration", 3600)) # 1 hour default
        num_slices = int(params.get("slices", 10)) # 10 slices default
        
        interval = duration_sec / num_slices
        total_units = float(req_data.get("units", 0.0))
        slice_units = total_units / num_slices
        
        logger.info(f"⏳ [TWAP] Start: {total_units} units in {num_slices} slices. Interval={interval}s")
        
        # Schedule each slice in Redis with a delay
        # We use a Priority Queue for execution, so we can't use BRPOP with delays easily.
        # Strategem: Instead of Rpush, we'll store the plan in Redis and
        # a dedicated 'AlgoTick' loop will pick it up, or use a background timer.
        
        # Simplified for V1: Loop and Push to Execution Queue directly (this worker thread stays active)
        # However, for an 8GB host, we don't want too many long-running tasks for 1 hour.
        # Better: Store the 'next_slice_time' in Redis for the parent_id.
        
        for i in range(num_slices):
            slice_req = req_data.copy()
            slice_req["units"] = slice_units
            slice_req["client_order_id"] = f"{req_data.get('client_order_id')}_slice_{i}"
            slice_req["parent_trade_id"] = str(parent_id)
            slice_req["risk_usd"] = float(req_data.get("risk_usd", 0.0)) / num_slices # Pro-rata risk
            
            # For pure TWAP, the first slice is immediate
            if i == 0:
                await rc.lpush("queue:execution:priority", json.dumps(slice_req))
            else:
                # Schedule in Redis via Sorted Set (Delayed Task pattern)
                delay = i * interval
                eta = asyncio.get_event_loop().time() + delay
                # Not using ZSET here as our worker only does BRPOP.
                # Let's use a background sleep within a task for now (Low overhead for small # of algos)
                asyncio.create_task(TwapAlgorithm.schedule_slice(rc, slice_req, delay))
                
        logger.info(f"✅ [TWAP] All {num_slices} slices scheduled for {parent_id}")

    @staticmethod
    async def schedule_slice(rc: Any, slice_req: dict, delay: float):
        """
        Wait for 'delay' seconds then push slice to the priority queue.
        """
        if delay > 0:
            await asyncio.sleep(delay)
            
        try:
            # Re-check Kill Switch before each slice
            if await rc.get("system:kill_switch") == "1":
                logger.warning(f"🛑 [TWAP] Slice rejected due to Global Kill Switch: {slice_req.get('client_order_id')}")
                return
                
            await rc.lpush("queue:execution:priority", json.dumps(slice_req))
            logger.info(f"✨ [TWAP] Slice Pushed: {slice_req.get('client_order_id')}")
        except Exception as e:
            logger.error(f"Error pushing TWAP slice: {e}")
