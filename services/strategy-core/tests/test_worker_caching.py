import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from uuid import uuid4
from app.workers.indicator_worker import IndicatorWorker
from app.models.market import MarketSymbol

@pytest.fixture
def mock_db_session():
    with patch('app.workers.indicator_worker.SessionLocal') as mock:
        yield mock

@pytest.fixture
def worker():
    w = IndicatorWorker()
    w.redis = AsyncMock()
    # Mock calculate sync to avoid true DB calls
    w._calculate_sync = MagicMock(return_value={"rsi": 50})
    return w

@pytest.mark.asyncio
async def test_refresh_cache_loads_active_symbols(worker, mock_db_session):
    # Setup Mock DB
    session = mock_db_session.return_value
    
    active_sym = MagicMock(spec=MarketSymbol)
    active_sym.symbol = "EUR_USD"
    active_sym.id = uuid4()
    active_sym.is_active = True
    
    # We can't easily mock the filter chain perfectly without complex setup, 
    # but we can mock the return value of .all()
    # The code does: db.query(MarketSymbol).filter(...).all()
    session.query.return_value.filter.return_value.all.return_value = [active_sym]
    
    await worker._refresh_cache()
    
    assert "EUR_USD" in worker.symbol_cache
    assert worker.symbol_cache["EUR_USD"] == active_sym.id

@pytest.mark.asyncio
async def test_process_message_skips_uncached_symbol(worker):
    worker.symbol_cache = {"EUR_USD": uuid4()} # Only EUR_USD is active
    
    # Test with inactive symbol
    fields = {"event_type": "candle_completed", "symbol": "GBP_JPY", "timeframe": "15m"}
    
    await worker.process_message("msg_id_1", fields)
    
    # Should NOT have called calculate
    worker._calculate_sync.assert_not_called()
    # Should NOT have published to redis
    worker.redis.xadd.assert_not_called()

@pytest.mark.asyncio
async def test_process_message_processes_cached_symbol(worker):
    active_id = uuid4()
    worker.symbol_cache = {"EUR_USD": active_id}
    
    fields = {"event_type": "candle_completed", "symbol": "EUR_USD", "timeframe": "15m", "timestamp": "2023-01-01"}
    
    await worker.process_message("msg_id_2", fields)
    
    # Should have called calculate with the ID
    worker._calculate_sync.assert_called_once_with(active_id, "EUR_USD", "15m")
    # Should have published
    worker.redis.xadd.assert_called_once()
    worker.redis.publish.assert_called_once()
