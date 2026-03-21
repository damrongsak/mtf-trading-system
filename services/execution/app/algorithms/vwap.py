import logging
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class VwapAlgorithm:
    @staticmethod
    async def execute(redis_client, db: AsyncSession, parent_id: str, req_data: dict):
        """
        Executes a VWAP (Volume-Weighted Average Price) algorithmic order.
        Slices the order based on a typical intraday volume profile.
        """
        params = req_data.get("algo_params", {})
        total_units = req_data.get("units")
        duration = params.get("duration", 3600)  # Total duration in seconds
        slices = params.get("slices", 6)          # Number of slices
        symbol = req_data.get("symbol")
        
        if slices < 1:
            slices = 1
            
        interval = duration / slices
        
        # Phase 1: Use a static U-Shaped Volume Profile (Typical for FX/Gold)
        # In a real system, this would be fetched from data-pipeline's volume buckets.
        weights = VwapAlgorithm._get_volume_profile(slices)
        
        logger.info(f"📊 [VWAP] Start: {total_units} units over {duration}s in {slices} slices.")
        logger.info(f"📊 [VWAP] Profile Weights: {weights}")
        
        for i in range(slices):
            slice_units = total_units * weights[i]
            # Ensure we don't have zero units due to rounding or profile
            if slice_units <= 0:
                continue
                
            delay = i * interval
            if i == 0:
                # First slice is immediate
                await VwapAlgorithm.schedule_slice(redis_client, parent_id, req_data, slice_units, i)
            else:
                # Subsequent slices are scheduled
                asyncio.create_task(
                    VwapAlgorithm._delayed_slice(redis_client, parent_id, req_data, slice_units, i, delay)
                )

        logger.info(f"✅ [VWAP] All {slices} slices scheduled for {parent_id}")

    @staticmethod
    def _get_volume_profile(num_slices: int) -> List[float]:
        """
        Returns a U-Shaped volume profile for the given number of slices.
        High volume at the start and end, low in the middle.
        """
        if num_slices == 1:
            return [1.0]
        
        # Simple U-shape generator
        # Strategy: Higher weights for i=0 and i=num_slices-1
        profile = []
        for i in range(num_slices):
            # Normalize index to 0..1
            x = i / (num_slices - 1)
            # Quadratic U-shape: 4*(x-0.5)^2 + offset
            # This gives 1.0 at x=0 and x=1, and 0.0 at x=0.5
            weight = 4 * (x - 0.5)**2 + 0.2
            profile.append(weight)
        
        # Normalize sum to 1.0
        total = sum(profile)
        return [w / total for w in profile]

    @staticmethod
    async def _delayed_slice(redis_client, parent_id: str, req_data: dict, units: float, slice_idx: int, delay: float):
        """Asynchronous delay before placing a slice."""
        await asyncio.sleep(delay)
        await VwapAlgorithm.schedule_slice(redis_client, parent_id, req_data, units, slice_idx)

    @staticmethod
    async def schedule_slice(redis_client, parent_id: str, req_data: dict, units: float, slice_idx: int):
        """Publishes a slice to the priority execution queue."""
        # Create slice request mapping parent attributes
        slice_req = req_data.copy()
        slice_req["units"] = units
        slice_req["parent_trade_id"] = parent_id
        slice_req["execution_algo"] = None # Child trades are executed normally
        slice_req["tag"] = f"VWAP_SLICE_{slice_idx}"

        # Standard lot scaling check would happen in OrderService, but here we just push to queue
        await redis_client.lpush("queue:execution:priority", json.dumps(slice_req))
        logger.info(f"🚀 [VWAP] Published slice {slice_idx} ({units} units) for parent {parent_id}")
