import asyncio
import logging
from typing import List, Callable, Awaitable
from app.streaming.adapters.base import StreamAdapter
from app.adapters.ctrader_client import AsyncCTraderClient
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoOAPayloadType
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASubscribeSpotsReq, ProtoOASpotEvent

logger = logging.getLogger(__name__)

class CTraderStreamer(StreamAdapter):
    def __init__(self, config: dict, callback: Callable[[dict], Awaitable[None]]):
        super().__init__(callback)
        self.host = config.get("host", "demo.ctraderapi.com")
        self.port = int(config.get("port", 5035))
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.account_id = int(config.get("account_id"))
        self.token = config.get("token")
        
        self.client = AsyncCTraderClient(self.host, self.port)
        self._stop_event = asyncio.Event()
        self._subscription_map = {} # Symbol -> SymbolID (Need mapping!)
        
    async def start(self, instruments: List[str]):
        logger.info(f"Starting cTrader Stream for {instruments}...")
        try:
            await self.client.connect()
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            # TODO: Resolve Symbol IDs
            # For MVP, assuming we have method or hardcoded map if needed.
            # Using get_symbols_list to find IDs
            symbols_list = await self.client.get_symbols_list(self.account_id)
            # Create Map
            sym_map = {s.symbolName: s.symbolId for s in symbols_list}
            
            ids_to_subscribe = []
            for instr in instruments:
                # Handle mapping (e.g. XAU/USD -> XAUUSD)
                clean_instr = instr.replace("/", "").replace("_", "")
                # Try exact match, then clean match
                sid = None
                for s_name, s_id in sym_map.items():
                    if s_name == instr or s_name == clean_instr:
                        sid = s_id
                        break
                
                if sid:
                    ids_to_subscribe.append(sid)
                    self._subscription_map[sid] = instr # Map ID back to requested name
                else:
                    logger.warning(f"Symbol {instr} not found in cTrader account.")
            
            if not ids_to_subscribe:
                logger.error("No valid symbols to subscribe.")
                return

            # Subscribe
            req = ProtoOASubscribeSpotsReq()
            req.ctidTraderAccountId = self.account_id
            req.symbolId.extend(ids_to_subscribe)
            req.subscribeToSpotTimestamp = True
            
            await self.client.send(req)
            logger.info(f"Subscribed to {len(ids_to_subscribe)} symbols.")
            
            # Start Loop to process incoming Spot Events
            # The client handles reading messages in background task.
            # We need to hook into the client to receive UNSOLICITED messages.
            # AsyncCTraderClient currently only resolves Futures.
            # I need to update AsyncCTraderClient to support a listener/callback for unsolicited messages.
            
            # HACK: monkey patch or subclass?
            # Better: Update AsyncCTraderClient to accept a generic callback.
            self.client.set_message_handler(self._on_message)
            
            await self._stop_event.wait()
            
        except Exception as e:
            logger.error(f"cTrader Streamer Error: {e}")
        finally:
            await self.client.disconnect()

    async def stop(self):
        logger.info("Stopping cTrader Stream...")
        self._stop_event.set()

    async def _on_message(self, msg):
        # Callback from client
        if msg.payloadType == ProtoOASpotEvent().payloadType:
            event = ProtoOASpotEvent()
            event.ParseFromString(msg.payload)
            
            symbol_id = event.symbolId
            symbol_name = self._subscription_map.get(symbol_id, f"ID:{symbol_id}")
            
            # Extract multiple prices? cTrader sends bid/ask changes.
            # We need to maintain state or just push what we have.
            # ProtoOASpotEvent has bid, ask, trendbar?
            
            bid = event.bid if event.HasField('bid') else None
            ask = event.ask if event.HasField('ask') else None
            
            # These are usually delta encoded or absolute?
            # Documentation says: "Bid price" (uint64). 
            # If standard int64, need to divide by 100000 etc?
            # We need symbol Digits.
            
            # MVP: Just log.
            # Real impl needs decoding logic.
            
            data = {
                "type": "PRICE",
                "source": "ctrader",
                "instrument": symbol_name,
                "time": str(datetime.utcnow()), # Approx
                "bid": float(bid) / 100000 if bid else 0.0, # Approximate scaling
                "ask": float(ask) / 100000 if ask else 0.0
            }
            await self.callback(data)
