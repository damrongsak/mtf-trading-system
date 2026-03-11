import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.adapters.ctrader import CTraderOrderAdapter
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATradeSide

@pytest.mark.asyncio
async def test_ctrader_get_order_book_success():
    # Setup adapter and client
    adapter = CTraderOrderAdapter(client_id="id", client_secret="secret", account_id="12345", token="token")
    adapter.client = AsyncMock()
    
    # Mock symbol resolution
    adapter._resolve_symbol_id_and_lot_size = AsyncMock(return_value=(1, 10000000, 100000))
    
    # Mock client.get_order_book return value
    mock_book = {
        "bids": [{"price": 2000.50, "volume": 100000}], 
        "asks": [{"price": 2000.60, "volume": 100000}]
    }
    adapter.client.get_order_book.return_value = mock_book
    
    # Execute
    result = await adapter.get_order_book("XAU_USD")
    
    # Verify
    assert result == mock_book
    adapter.client.connect.assert_called_once()
    adapter.client.authorize_app.assert_called_once()
    adapter.client.authorize_account.assert_called_once()
    adapter.client.get_order_book.assert_called_once_with(12345, 1)

@pytest.mark.asyncio
async def test_ctrader_client_get_order_book_logic():
    # Test the low-level AsyncCTraderClient.get_order_book logic (the one-shot pattern)
    from app.adapters.ctrader_client import AsyncCTraderClient
    client = AsyncCTraderClient(host="host", port=123)
    client._connected = True
    client.writer = MagicMock()
    client.writer.drain = AsyncMock()
    
    # Mock Send to return a successful subscription response
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASubscribeDepthQuotesRes, ProtoOADepthEvent
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOADepthQuote
    
    sub_res_msg = ProtoMessage(payloadType=ProtoOASubscribeDepthQuotesRes().payloadType, payload=b"")
    client.send = AsyncMock(return_value=sub_res_msg)
    client._send_proto_message = AsyncMock()
    
    # Prepare the Depth event that will trigger the future
    event = ProtoOADepthEvent()
    event.ctidTraderAccountId = 12345
    event.symbolId = 1
    
    q1 = event.newQuotes.add()
    q1.id = 1
    q1.bid = 200050000 # 2000.50 * 100000
    q1.size = 500000
    
    q2 = event.newQuotes.add()
    q2.id = 2
    q2.ask = 200060000 # 2000.60 * 100000
    q2.size = 500000
    
    event_msg = ProtoMessage(
        payloadType=event.payloadType,
        payload=event.SerializeToString()
    )

    # Trigger the handler in a task
    async def trigger_event():
        await asyncio.sleep(0.1)
        client._message_handler(event_msg)
        
    asyncio.create_task(trigger_event())
    
    # Execute
    result = await client.get_order_book(12345, 1, timeout=1.0)
    
    # Verify
    assert "bids" in result
    assert result["bids"][0]["price"] == 2000.50
    assert result["bids"][0]["volume"] == 500000.0
    assert result["asks"][0]["price"] == 2000.60
    assert result["asks"][0]["volume"] == 500000.0
