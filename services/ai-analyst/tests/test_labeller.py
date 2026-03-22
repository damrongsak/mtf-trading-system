import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from app.services.labeller import AutomatedLabeller
from app.models.candle import Candle

@pytest.mark.asyncio
async def test_label_historical_candles_success():
    """Verify that labeller correctly identifies valid vs fake sweeps."""
    labeller = AutomatedLabeller()
    mock_session = AsyncMock()
    
    # 1. Create synthetic candles: A high sweep at index 5
    # Highs: [2, 2, 2, 2, 2, 10, 2, 2, 2, 2] -> Recent high is 2, sweep at 10
    prices = [100.0] * 20
    highs = [102.0] * 20
    highs[10] = 110.0 # Bearish Sweep
    
    # Post-sweep price action:
    # Candle 10: Close 105
    # Candle 13 (idx+3): Close 95 (Valid reversal)
    closes = [101.0] * 20
    closes[10] = 105.0
    closes[13] = 95.0
    
    mock_candles = []
    for i in range(20):
        c = MagicMock(spec=Candle)
        c.timestamp = pd.Timestamp(2023, 1, 1) + pd.Timedelta(minutes=i*15)
        c.open = 100.0
        c.high = highs[i]
        c.low = 98.0
        c.close = closes[i]
        c.volume = 1000
        c.ai_labels = {}
        mock_candles.append(c)
        
    # Mock DB response
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = list(reversed(mock_candles))
    mock_session.execute.return_value = mock_result
    
    # Mock indicators to ensure we get a sweep at index 10
    with patch("app.services.labeller.detect_liquidity_sweeps") as mock_detect:
        mock_detect.return_value = [{
            "type": "bearish_sweep",
            "index": 10,
            "timestamp": "...",
            "level": 102.0,
            "meta": {}
        }]
        
        await labeller.label_historical_candles(mock_session, "XAUUSD", "M15")
        
        # Verifycandle at index 10 was updated with 'valid_bearish_sweep'
        # Note: in labeller.py candles are reversed back to chronological
        updated_candle = mock_candles[10]
        assert updated_candle.ai_labels['sweep_type'] == "valid_bearish_sweep"
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_label_historical_candles_fake_sweep():
    """Verify that labeller identifies fake sweeps (continuation)."""
    labeller = AutomatedLabeller()
    mock_session = AsyncMock()
    
    # Candle 10: Bearish sweep (High 110 > Level 102)
    # Candle 13 (idx+3): Close 120 (Continuation - Fake reversal)
    mock_candles = [MagicMock(spec=Candle, high=102, close=101, ai_labels={}) for _ in range(20)]
    mock_candles[10].high = 110.0
    mock_candles[10].close = 105.0
    mock_candles[13].close = 120.0
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = list(reversed(mock_candles))
    mock_session.execute.return_value = mock_result
    
    with patch("app.services.labeller.detect_liquidity_sweeps") as mock_detect:
        mock_detect.return_value = [{
            "type": "bearish_sweep",
            "index": 10,
            "timestamp": "...",
            "level": 102.0,
            "meta": {}
        }]
        
        await labeller.label_historical_candles(mock_session, "XAUUSD", "M15")
        
        updated_candle = mock_candles[10]
        assert updated_candle.ai_labels['sweep_type'] == "fake_bearish_sweep"
