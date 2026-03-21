import logging
import json
from typing import Dict, Any
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class RiskParityEngine:
    """
    Institutional Risk Parity Engine (Phase 11).
    Calculates and scales risk based on Fund 'scale_factor' and asset-specific performance.
    """

    @staticmethod
    async def get_scale_multiplier(fund_id: str, knowledge_score: float = 1.0) -> float:
        """
        Combines the Fund's rigid 'scale_factor' with the dynamic 'knowledge_score'.
        Formula: multiplier = fund.scale_factor * knowledge_score
        """
        from app.services.cache_service import execution_cache
        fund_data = await execution_cache.get_fund(fund_id)
        if not fund_data:
            return 1.0 * knowledge_score
        
        scale_factor = float(fund_data.get("scale_factor", 1.0))
        multiplier = scale_factor * knowledge_score
        
        if multiplier != 1.0:
            logger.info(f"⚖️ [ParityEngine] Institutional Scaling: {scale_factor}x Fund * {knowledge_score}x Knowledge = {multiplier}x Total")
            
        return multiplier

    @staticmethod
    async def calculate_parity_size(fund_id: str, symbol: str, equity: float, current_price: float) -> float:
        """
        Retrieves the pre-calculated parity weight for a symbol and returns target units.
        Weights are updated periodically by a background task (using PortfolioOptimizer).
        """
        rc = get_redis_client()
        weights_json = await rc.get(f"fund:{fund_id}:risk_parity_weights")
        
        if not weights_json:
            return 0.0
            
        try:
            weights = json.loads(weights_json)
            target_weight = float(weights.get(symbol, 0.0))
            
            if target_weight <= 0:
                return 0.0
                
            risk_capital = equity * target_weight
            units = risk_capital / current_price
            
            logger.info(f"⚖️ [ParityEngine] {symbol} Weight: {target_weight:.4f} -> ${risk_capital:.2f} Capital")
            return units
        except Exception as e:
            logger.error(f"Error calculating parity size: {e}")
            return 0.0
