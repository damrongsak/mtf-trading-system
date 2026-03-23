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
    async def get_scale_multiplier(
        fund_id: str, 
        symbol: str, 
        direction: str = "LONG", 
        knowledge_score: float = 1.0
    ) -> float:
        """
        Calculates complex institutional multiplier:
        Multiplier = FundScaleFactor * Km (Knowledge) * Ks (Sentiment)
        """
        from app.services.cache_service import execution_cache
        
        # 1. Base Fund Scaling
        fund_data = await execution_cache.get_fund(fund_id)
        scale_factor = float(fund_data.get("scale_factor", 1.0)) if fund_data else 1.0
        
        # 2. AI Sentiment Scaling (Ks)
        # Stored in Redis by ai-analyst as sentiment:{symbol} -> {"score": float, ...}
        rc = get_redis_client()
        ks = 1.0
        sentiment_json = await rc.get(f"sentiment:{symbol}")
        
        if sentiment_json:
            try:
                sentiment_data = json.loads(sentiment_json)
                score = float(sentiment_data.get("score", 0.0))
                
                # Directional Alignment Logic
                is_bullish = score >= 0.3
                is_bearish = score <= -0.3
                
                if (direction.upper() in ["LONG", "BUY", "BULLISH"] and is_bullish) or \
                   (direction.upper() in ["SHORT", "SELL", "BEARISH"] and is_bearish):
                    # Alignment! Boost risk based on conviction (max 1.25x)
                    ks = 1.0 + (abs(score) / 4.0) 
                    logger.info(f"🚀 [SentimentAlignment] {symbol} {direction} align with {score} sentiment. Ks: {ks:.2f}x")
                elif (direction.upper() in ["LONG", "BUY", "BULLISH"] and is_bearish) or \
                     (direction.upper() in ["SHORT", "SELL", "BEARISH"] and is_bullish):
                    # Conflict! Protective cut (0.5x)
                    ks = 0.5
                    logger.warning(f"⚠️ [SentimentConflict] {symbol} {direction} conflicts with {score} sentiment. Ks: 0.50x (Protective Cut)")
                else:
                    # Neutral or low conviction
                    ks = 1.0
            except Exception as e:
                logger.error(f"Error parsing sentiment for {symbol}: {e}")
                ks = 1.0

        # 3. AI Correlation Scaling (Kc) [PHASE 40]
        kc = 1.0
        correlation_json = await rc.get(f"fund:{fund_id}:correlation_stats")
        if correlation_json:
            try:
                corr_data = json.loads(correlation_json)
                if corr_data.get("systemic_alert"):
                    # Check if this asset is systemic (PC1 loading > 0.6)
                    high_corr_assets = corr_data.get("high_correlation_assets", [])
                    if symbol in high_corr_assets:
                        # Check for existing exposure in other systemic assets
                        # Note: fund:{id}:active_symbols is a Redis SET maintained by Fill/Close consumers
                        active_symbols = await rc.smembers(f"fund:{fund_id}:active_symbols")
                        
                        # Filter out the current symbol being evaluated
                        other_active_systemic = [s for s in active_symbols if s in high_corr_assets and s != symbol]
                        
                        if other_active_systemic:
                            # We have overlapping factor exposure!
                            kc = 0.7
                            logger.warning(
                                f"🛡️ [CorrelationGuard] Overlapping factor exposure for {symbol}. "
                                f"Already active: {other_active_systemic}. Kc: 0.70x"
                            )
            except Exception as e:
                logger.error(f"Error parsing correlation for {fund_id}: {e}")

        multiplier = scale_factor * knowledge_score * ks * kc
        
        if multiplier != 1.0:
            logger.info(
                f"⚖️ [ParityEngine] Institutional Scaling: "
                f"{scale_factor}x Fund * {knowledge_score}x Km * {ks:.2f}x Ks * {kc:.2f}x Kc = {multiplier:.2f}x Total"
            )
            
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
