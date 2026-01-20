
import pytest
from unittest.mock import AsyncMock, Mock
from app.streaming.manager import ConnectionManager
from fastapi import WebSocket

@pytest.mark.asyncio
async def test_broadcast_filtering():
    # Force a fresh instance if singleton prevents it, or just use the global one but clear it
    manager = ConnectionManager()
    manager.active_connections.clear()
    
    # Mock WebSockets
    ws_all = AsyncMock(spec=WebSocket)
    ws_oanda = AsyncMock(spec=WebSocket)
    ws_ctrader = AsyncMock(spec=WebSocket)
    
    symbol = "EUR_USD"
    
    # Helper to simulate connect since it's async and we want to verify internal state if needed
    # But checking broadcast effect is better
    await manager.connect(ws_all, [symbol], source=None)
    await manager.connect(ws_oanda, [symbol], source="OANDA")
    await manager.connect(ws_ctrader, [symbol], source="CTRADER")
    
    # Test 1: Message with OANDA source
    msg_oanda = '{"type": "PRICE", "source": "OANDA", "bid": 1.0}'
    await manager.broadcast(symbol, msg_oanda)
    
    # ws_all should receive (filter=None)
    ws_all.send_text.assert_called_with(msg_oanda)
    # ws_oanda should receive (filter=OANDA == msg=OANDA)
    ws_oanda.send_text.assert_called_with(msg_oanda)
    # ws_ctrader should NOT receive (filter=CTRADER != msg=OANDA)
    ws_ctrader.send_text.assert_not_called()
    
    # Reset mocks
    ws_all.reset_mock()
    ws_oanda.reset_mock()
    ws_ctrader.reset_mock()
    
    # Test 2: Message with CTRADER source
    msg_ctrader = '{"type": "PRICE", "source": "CTRADER", "bid": 2.0}'
    await manager.broadcast(symbol, msg_ctrader)
    
    ws_all.send_text.assert_called_with(msg_ctrader)
    ws_oanda.send_text.assert_not_called()
    ws_ctrader.send_text.assert_called_with(msg_ctrader)
    
    # Reset
    ws_all.reset_mock()
    ws_oanda.reset_mock()
    ws_ctrader.reset_mock()

    # Test 3: Message with NO source (e.g. legacy or unknown)
    msg_nosource = '{"type": "PRICE", "bid": 3.0}'
    await manager.broadcast(symbol, msg_nosource)
    
    ws_all.send_text.assert_called_with(msg_nosource)
    # Filters should BLOCK if they expect a source but none is present
    ws_oanda.send_text.assert_not_called() 
    ws_ctrader.send_text.assert_not_called()
