import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.scheduler_tasks import check_sentiment_risk_drift

@pytest.mark.asyncio
async def test_sentiment_drift_throttle():
    """
    Verifies that check_sentiment_risk_drift respects the Redis throttle key.
    """
    # 1. Mock Services
    mock_redis = AsyncMock()
    mock_sentiment = AsyncMock()
    mock_risk_rebalancer = AsyncMock()
    
    # Mock SentimentService having its own redis client (as used in scheduler_tasks.py)
    mock_sentiment.redis = AsyncMock()
    
    services_map = {
        "redis": mock_redis,
        "sentiment": mock_sentiment,
        "risk_rebalancer": mock_risk_rebalancer
    }
    
    # 2. Setup Mock Data
    mock_sentiment.get_sentiment.return_value = {"score": 0.5, "reason": "Markets are moving"}
    
    # Mock DB: One active fund
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = [{"id": "f132981c-fund-uuid"}]
    
    # Mock RiskRebalancer recommendation
    mock_risk_rebalancer.analyze_risk.return_value = {
        "scratchpad": ["AI suggests rebalance: {\"risk_percentage\": 0.035, \"max_drawdown_threshold\": 1.2}"]
    }

    # Helper for sequential redis.get calls
    # Sequence: 
    # 1. prev_score
    # 2. throttle_check for fund
    # 3. prev_score (second run)
    # 4. throttle_check for fund (second run)
    mock_sentiment.redis.get.side_effect = ["0.0", None, "0.5", "1"]

    with patch("app.core.scheduler_tasks.services", services_map), \
         patch("app.core.scheduler_tasks.SessionLocal", return_value=mock_db), \
         patch("app.core.scheduler_tasks.send_telegram_message", new_callable=AsyncMock) as mock_send_tel, \
         patch("app.core.scheduler_tasks._notify_fund_owners", new_callable=AsyncMock) as mock_notify:
        
        # --- EXECUTION 1: No Throttle ---
        await check_sentiment_risk_drift()
        
        # Verify rebalancer was called
        assert mock_risk_rebalancer.analyze_risk.call_count == 1
        # Verify notification was attempted
        assert mock_notify.called
        
        # --- EXECUTION 2: Throttle Active ---
        # (side_effect will now return "1" for the throttle check)
        await check_sentiment_risk_drift()
        
        # Risk rebalancer should NOT be called again (it was throttled at line 168 of scheduler_tasks.py)
        assert mock_risk_rebalancer.analyze_risk.call_count == 1
        
        print("\n✅ Alert throttling verified: Redundant check blocked by Redis cooldown.")

if __name__ == "__main__":
    asyncio.run(test_sentiment_drift_throttle())
