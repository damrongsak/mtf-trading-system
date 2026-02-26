import asyncio
import logging
import struct
import time
from typing import Optional, Dict
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage, ProtoHeartbeatEvent
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

logger = logging.getLogger(__name__)

class AsyncCTraderClient:
    def __init__(self, host: str, port: int, ssl: bool = True):
        self.host = host
        self.port = port
        self.ssl = ssl
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._app_authorized = False
        self._account_authorized = False
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_handler = None
        self._auth_lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()

    def set_message_handler(self, handler):
        """Set a callback for unsolicited messages (e.g. Spot Events)"""
        self._message_handler = handler

    async def connect(self):
        async with self._connect_lock:
            if self._connected:
                return

            logger.info(f"Connecting to cTrader {self.host}:{self.port}...")
            try:
                self.reader, self.writer = await asyncio.open_connection(
                    self.host, self.port, ssl=self.ssl
                )
                self._connected = True
                logger.info("Connected to cTrader.")
                
                # Start reader loop
                self._reader_task = asyncio.create_task(self._read_loop())
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            except Exception as e:
                logger.error(f"Failed to connect to cTrader: {e}")
                raise

    async def disconnect(self):
        self._connected = False
        self._app_authorized = False
        self._account_authorized = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._reader_task:
            self._reader_task.cancel()
            
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
        self.writer = None
        self.reader = None
        logger.info("Disconnected from cTrader.")

    async def _read_loop(self):
        try:
            while self._connected:
                # Read 4 bytes length (Big Endian Int32)
                length_bytes = await self.reader.readexactly(4)
                length = struct.unpack(">I", length_bytes)[0]
                
                # Check for sane length
                if length > 10_000_000:
                    logger.warning(f"Message too large: {length} bytes")
                    await self.reader.readexactly(length) # Drain?
                    continue

                if length > 0:
                    data = await self.reader.readexactly(length)
                    await self._process_message(data)
                    
        except asyncio.IncompleteReadError:
            logger.warning("Connection closed by peer (IncompleteRead).")
            await self.disconnect()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in read loop: {e}")
            await self.disconnect()

    async def _process_message(self, data: bytes):
        try:
            msg = ProtoMessage()
            msg.ParseFromString(data)
            
            client_msg_id = msg.clientMsgId
            
            # Handle Heartbeat response (PayloadType 51 is Heartbeat Event)
            if msg.payloadType == 51: # ProtoHeartbeatEvent().payloadType
                # logger.debug("Heartbeat received")
                return

            # Resolve Future if pending
            if client_msg_id and client_msg_id in self._response_futures:
                fut = self._response_futures.pop(client_msg_id)
                if not fut.done():
                    fut.set_result(msg)
            else:
                # Handle unsolicited messages
                if self._message_handler:
                    try:
                        self._message_handler(msg)
                    except Exception as he:
                        logger.error(f"Message handler error: {he}")
                        # If handler is async, we should await it?
                        # Since we are in an async function _process_message, we can.
                        # But self._message_handler might be sync or async.
                        # Let's support async check.
                        if asyncio.iscoroutinefunction(self._message_handler):
                            asyncio.create_task(self._message_handler(msg)) # Fire and forget

                
        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    async def _heartbeat_loop(self):
        while self._connected:
            try:
                await asyncio.sleep(10)
                await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await self.disconnect()
                break

    async def send_heartbeat(self):
        msg = ProtoHeartbeatEvent()
        # Wrap in ProtoMessage
        wrapper = ProtoMessage(
            payloadType=msg.payloadType,
            payload=msg.SerializeToString()
        )
        await self._send_proto_message(wrapper)

    async def send(self, payload_obj, client_msg_id: str = None) -> ProtoMessage:
        """
        Send a Protobuf payload and wait for response.
        """
        if not self._connected:
            raise ConnectionError("Not connected")

        if not client_msg_id:
            client_msg_id = str(int(time.time() * 1000000))

        # Wrap payload
        wrapper = ProtoMessage(
            payloadType=payload_obj.payloadType,
            payload=payload_obj.SerializeToString(),
            clientMsgId=client_msg_id
        )
        
        # Create Future
        fut = asyncio.get_running_loop().create_future()
        self._response_futures[client_msg_id] = fut
        
        # Send
        await self._send_proto_message(wrapper)
        
        # Wait
        return await fut

    async def _send_proto_message(self, msg: ProtoMessage):
        data = msg.SerializeToString()
        length = len(data)
        header = struct.pack(">I", length)
        
        self.writer.write(header + data)
        await self.writer.drain()

    async def authorize_app(self, client_id: str, client_secret: str):
        async with self._auth_lock:
            if self._app_authorized:
                return True

            req = ProtoOAApplicationAuthReq()
            req.clientId = client_id
            req.clientSecret = client_secret
            
            resp_msg = await self.send(req)
            
            # Extract response
            if resp_msg.payloadType == ProtoOAApplicationAuthRes().payloadType:
                self._app_authorized = True
                return True
            elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
                error = ProtoOAErrorRes()
                error.ParseFromString(resp_msg.payload)
                raise Exception(f"App Auth Error: {error.errorCode} - {error.description}")
            else:
                 raise Exception(f"Unexpected response type: {resp_msg.payloadType}")
             
    async def authorize_account(self, account_id: int, token: str):
        async with self._auth_lock:
            if self._account_authorized:
                return True

            req = ProtoOAAccountAuthReq()
            req.ctidTraderAccountId = int(account_id)
            req.accessToken = token
            
            resp_msg = await self.send(req)
            
            if resp_msg.payloadType == ProtoOAAccountAuthRes().payloadType:
                self._account_authorized = True
                return True
            elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
                error = ProtoOAErrorRes()
                error.ParseFromString(resp_msg.payload)
                # Handle case where server thinks we are already logged in but client state was reset
                if error.errorCode == "ALREADY_LOGGED_IN":
                    logger.info(f"Account {account_id} already logged in on server. Updating client state.")
                    self._account_authorized = True
                    return True
                raise Exception(f"Account Auth Error: {error.errorCode} - {error.description}")
            else:
                 raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def get_symbols_list(self, account_id: int):
        req = ProtoOASymbolsListReq()
        req.ctidTraderAccountId = int(account_id)
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOASymbolsListRes().payloadType:
            res = ProtoOASymbolsListRes()
            res.ParseFromString(resp_msg.payload)
            return res.symbol 
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Get Symbols Error: {error.errorCode}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def get_symbols_full(self, account_id: int, symbol_ids: list):
        """
        Fetch full symbol details (digits, pipPosition, etc.) for a list of IDs.
        """
        req = ProtoOASymbolByIdReq()
        req.ctidTraderAccountId = int(account_id)
        req.symbolId.extend([int(x) for x in symbol_ids])
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOASymbolByIdRes().payloadType:
            res = ProtoOASymbolByIdRes()
            res.ParseFromString(resp_msg.payload)
            return res.symbol # List of ProtoOASymbol
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Get Symbols Full Error: {error.errorCode}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")
             
    async def get_trendbars(self, account_id: int, symbol_id: int, period: int, count: int = None, from_timestamp: int = None, to_timestamp: int = None):
        """
        Fetch historical trendbars (candles).
        period: Enum ProtoOATrendbarPeriod (e.g. M1=1, M15=3, H1=4)
        timestamps: Unix timestamp in Milliseconds
        """
        req = ProtoOAGetTrendbarsReq()
        req.ctidTraderAccountId = int(account_id)
        req.symbolId = int(symbol_id)
        req.period = period
        if count is not None: req.count = count
        if from_timestamp is not None: req.fromTimestamp = from_timestamp
        if to_timestamp is not None: req.toTimestamp = to_timestamp
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOAGetTrendbarsRes().payloadType:
            res = ProtoOAGetTrendbarsRes()
            res.ParseFromString(resp_msg.payload)
            return res.trendbar # list of trendbars
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Get Trendbars Error: {error.errorCode}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def get_tick_data(self, account_id: int, symbol_id: int, quote_type: int, from_timestamp: int, to_timestamp: int):
        """
        Fetch historical tick data.
        quote_type: 1 (Bid), 2 (Ask)
        timestamps: Unix timestamp in Milliseconds
        """
        req = ProtoOAGetTickDataReq()
        req.ctidTraderAccountId = int(account_id)
        req.symbolId = int(symbol_id)
        req.type = quote_type
        req.fromTimestamp = int(from_timestamp)
        req.toTimestamp = int(to_timestamp)
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOAGetTickDataRes().payloadType:
            res = ProtoOAGetTickDataRes()
            res.ParseFromString(resp_msg.payload)
            return res.tickData # list of ticks (delta encoded)
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Get Ticks Error: {error.errorCode}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def refresh_token(self, refresh_token: str):
        """
        Refresh the access token using the refresh token.
        Returns: Tuple(new_access_token, new_refresh_token, expires_in, refresh_expires_in)
        """
        req = ProtoOARefreshTokenReq()
        req.refreshToken = refresh_token
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOARefreshTokenRes().payloadType:
            res = ProtoOARefreshTokenRes()
            res.ParseFromString(resp_msg.payload)
            return res.accessToken, res.refreshToken, res.expiresIn, getattr(res, 'reauthorizationTokenExpiresIn', None)
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Refresh Token Error: {error.errorCode} - {error.description}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")
    async def get_account_list(self, token: str):
        """
        Fetch the list of accounts linked to the given Access Token.
        """
        req = ProtoOAGetAccountListByAccessTokenReq()
        req.accessToken = token
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOAGetAccountListByAccessTokenRes().payloadType:
            res = ProtoOAGetAccountListByAccessTokenRes()
            res.ParseFromString(resp_msg.payload)
            return res.ctidTraderAccount
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Get Account List Error: {error.errorCode} - {error.description}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def get_trader(self, account_id: int):
        """
        Fetch Trader details (Balance, etc.) using ProtoOATraderReq.
        """
        req = ProtoOATraderReq()
        req.ctidTraderAccountId = int(account_id)
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOATraderRes().payloadType:
            res = ProtoOATraderRes()
            res.ParseFromString(resp_msg.payload)
            return res.trader
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Get Trader Error: {error.errorCode} - {error.description}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def create_order(self, account_id: int, symbol_id: int, order_type: int, trade_side: int, volume: int, 
                           price: Optional[float] = None, sl: Optional[float] = None, tp: Optional[float] = None,
                           comment: Optional[str] = None):
        req = ProtoOANewOrderReq()
        req.ctidTraderAccountId = int(account_id)
        req.symbolId = int(symbol_id)
        req.orderType = order_type 
        req.tradeSide = trade_side
        req.volume = int(volume)
        
        if price is not None: req.limitPrice = float(price)
        if sl is not None: req.stopLoss = float(sl)
        if tp is not None: req.takeProfit = float(tp)
        if comment: req.comment = comment
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOAExecutionEvent().payloadType:
            # cTrader returns ExecutionEvent for new orders
            res = ProtoOAExecutionEvent()
            res.ParseFromString(resp_msg.payload)
            return res
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Create Order Error: {error.errorCode} - {error.description}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def cancel_order(self, account_id: int, order_id: int):
        req = ProtoOACancelOrderReq()
        req.ctidTraderAccountId = int(account_id)
        req.orderId = int(order_id)
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOAExecutionEvent().payloadType:
            res = ProtoOAExecutionEvent()
            res.ParseFromString(resp_msg.payload)
            return res
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Cancel Order Error: {error.errorCode} - {error.description}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def get_reconcile(self, account_id: int):
        req = ProtoOAReconcileReq()
        req.ctidTraderAccountId = int(account_id)
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOAReconcileRes().payloadType:
            res = ProtoOAReconcileRes()
            res.ParseFromString(resp_msg.payload)
            return res # Contains .position list
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Reconcile Error: {error.errorCode} - {error.description}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def close_position(self, account_id: int, position_id: int, volume: int):
        req = ProtoOAClosePositionReq()
        req.ctidTraderAccountId = int(account_id)
        req.positionId = int(position_id)
        req.volume = int(volume)
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOAExecutionEvent().payloadType:
            res = ProtoOAExecutionEvent()
            res.ParseFromString(resp_msg.payload)
            return res
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Close Position Error: {error.errorCode} - {error.description}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def get_deal_list(self, account_id: int, from_timestamp: int, to_timestamp: int):
        """
        Fetch historical deals (closed trades).
        timestamps: Unix timestamp in Milliseconds
        """
        req = ProtoOADealListReq()
        req.ctidTraderAccountId = int(account_id)
        req.fromTimestamp = int(from_timestamp)
        req.toTimestamp = int(to_timestamp)
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOADealListRes().payloadType:
            res = ProtoOADealListRes()
            res.ParseFromString(resp_msg.payload)
            return res.deal # list of ProtoOADeal
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Get Deal List Error: {error.errorCode} - {error.description}")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")
