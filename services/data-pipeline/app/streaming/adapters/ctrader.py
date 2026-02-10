import asyncio
import logging
from typing import List, Callable, Awaitable
from app.streaming.adapters.base import StreamAdapter
from app.adapters.ctrader_client import AsyncCTraderClient
from datetime import datetime
# from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoOAPayloadType
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
        self._digits_map = {} # SymbolID -> Digits
        self._last_quotes = {} # SymbolID -> {bid, ask}
        
    async def start(self, instruments: List[str]):
        logger.info(f"Starting cTrader Stream for {instruments}...")
        try:
            await self.client.connect()
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            # 1. Resolve Symbol IDs and Digits
            # We first need the list to find IDs
            symbols_list = await self.client.get_symbols_list(self.account_id)
            # Create Map: Name -> ID
            sym_map = {s.symbolName: s.symbolId for s in symbols_list}
            
            ids_to_subscribe = []
            ids_for_details = []

            for instr in instruments:
                # Handle mapping (e.g. XAU/USD -> XAUUSD)
                clean_instr = instr.replace("/", "").replace("_", "")
                
                sid = None
                # Try exact match, then clean match
                for s_name, s_id in sym_map.items():
                    if s_name == instr or s_name == clean_instr:
                        sid = s_id
                        break
                
                if sid:
                    ids_to_subscribe.append(sid)
                    ids_for_details.append(sid)
                    self._subscription_map[sid] = instr # Map ID back to requested name
                else:
                    logger.warning(f"Symbol {instr} not found in cTrader account.")
            
            if not ids_to_subscribe:
                logger.error("No valid symbols to subscribe.")
                return

            # 2. Fetch Symbol Details (Digits)
            # cTrader requires fetching details to know precision (digits)
            if ids_for_details:
                full_symbols = await self.client.get_symbols_full(self.account_id, ids_for_details)
                for fs in full_symbols:
                    # Default to 5 digits if missing, but usually present
                    digits = fs.digits if fs.HasField('digits') else 5
                    self._digits_map[fs.symbolId] = digits
                    logger.debug(f"Symbol {fs.symbolId} digits: {digits}")
                    
                    # Publish Symbol Details for ECST
                    symbol_name = self._subscription_map.get(fs.symbolId)
                    if symbol_name:
                        # Convert Protobuf to dict for serialization
                        details = {}
                        for field, value in fs.ListFields():
                            details[field.name] = value
                        
                        await self.callback({
                            "type": "SYMBOL_DETAILS",
                            "source": "ctrader",
                            "instrument": symbol_name,
                            "details": details
                        })

            # 3. Subscribe
            req = ProtoOASubscribeSpotsReq()
            req.ctidTraderAccountId = self.account_id
            req.symbolId.extend(ids_to_subscribe)
            req.subscribeToSpotTimestamp = True
            
            await self.client.send(req)
            logger.info(f"Subscribed to {len(ids_to_subscribe)} symbols.")
            
            # 4. Set Message Handler
            self.client.set_message_handler(self._on_message)
            
            await self._stop_event.wait()
            
        except Exception as e:
            logger.error(f"cTrader Streamer Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            await self.client.disconnect()

    async def stop(self):
        logger.info("Stopping cTrader Stream...")
        self._stop_event.set()

    def _calculate_price(self, raw_price):
        """
        Convert raw integer price to float.
        Observation: cTrader (IC Markets) seems to send all prices scaled by 10^5 
        regardless of the 'digits' metadata.
        """
        if raw_price is None:
            return None
        return float(raw_price) / 100000.0

    async def _on_message(self, msg):
        # Callback from client
        if msg.payloadType == ProtoOASpotEvent().payloadType:
            event = ProtoOASpotEvent()
            event.ParseFromString(msg.payload)
            
            symbol_id = event.symbolId
            symbol_name = self._subscription_map.get(symbol_id, f"ID:{symbol_id}")
            # digits = self._digits_map.get(symbol_id, 5) # Unreliable for scaling, ignoring.
            
            # --- State Management for Partial Updates ---
            
            current_state = self._last_quotes.get(symbol_id, {"bid": 0.0, "ask": 0.0})
            
            # Update Bid
            if event.HasField('bid'):
                current_state["bid"] = self._calculate_price(event.bid)
                
            # Update Ask
            if event.HasField('ask'):
                current_state["ask"] = self._calculate_price(event.ask)
            
            # Save state
            self._last_quotes[symbol_id] = current_state
            
            # Check if we have valid prices
            if current_state["bid"] == 0.0 and current_state["ask"] == 0.0:
                return # Parsing or initialization issue

            data = {
                "type": "PRICE",
                "source": "ctrader",
                "instrument": symbol_name,
                "time": str(datetime.utcnow()), 
                "bid": current_state["bid"],
                "ask": current_state["ask"],
                "status": "tradeable" # Assume tradeable if streaming
            }
            await self.callback(data)
