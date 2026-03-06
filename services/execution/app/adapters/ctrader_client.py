import asyncio
import logging
import struct
import time
from typing import Optional, Dict, Any
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
        
        # Circuit Breaker state
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._circuit_broken_until = 0.0
        self._max_failures = 5
        self._cooldown_period = 300 # 5 minutes

    def set_message_handler(self, handler):
        """Set a callback for unsolicited messages (e.g. Spot Events)"""
        self._message_handler = handler

    async def connect(self):
        async with self._connect_lock:
            if self._connected:
                return

            # Circuit Breaker Check
            now = time.time()
            if now < self._circuit_broken_until:
                remaining = int(self._circuit_broken_until - now)
                raise ConnectionError(f"Circuit Breaker active. Cooldown remaining: {remaining}s")

            logger.info(f"Connecting to cTrader {self.host}:{self.port}...")
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port, ssl=self.ssl),
                    timeout=10.0
                )
                self.reader = reader
                self.writer = writer
                
                # Optimizer: Disable Nagle's Algorithm for HFT-lite (Lower Latency)
                sock = self.writer.get_extra_info('socket')
                if sock:
                    import socket
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    logger.debug("TCP_NODELAY enabled for cTrader connection")
                self._connected = True
                self._failure_count = 0 # Reset on success
                logger.info("Connected to cTrader.")
                
                # Start reader loop
                self._reader_task = asyncio.create_task(self._read_loop())
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            except Exception as e:
                self._failure_count += 1
                logger.error(f"Failed to connect to cTrader (Failure {self._failure_count}/{self._max_failures}): {e}")
                
                if self._failure_count >= self._max_failures:
                    self._circuit_broken_until = time.time() + self._cooldown_period
                    logger.warning(f"Circuit Breaker TRIPPED. Cooldown for {self._cooldown_period}s")
                
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

    async def send(self, payload_obj, client_msg_id: str = None, timeout: float = 10.0) -> ProtoMessage:
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
        
        try:
            # Send
            await self._send_proto_message(wrapper)
            
            # Wait with timeout
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            if client_msg_id in self._response_futures:
                del self._response_futures[client_msg_id]
            logger.error(f"Timeout waiting for cTrader response (Type: {payload_obj.payloadType}, ID: {client_msg_id})")
            raise
        except Exception as e:
            if client_msg_id in self._response_futures:
                del self._response_futures[client_msg_id]
            raise

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
            
            # Check for rejection
            if res.executionType == ProtoOAExecutionType.ORDER_REJECTED:
                error_code = res.errorCode if res.HasField("errorCode") else "UNKNOWN"
                raise Exception(f"cTrader Order REJECTED: {error_code}")
                
            return res
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Create Order Error: {error.errorCode} - {error.description}")
        elif resp_msg.payloadType == ProtoOAOrderErrorEvent().payloadType:
             error = ProtoOAOrderErrorEvent()
             error.ParseFromString(resp_msg.payload)
             # payloadType 2132 usually means a trading-related error (e.g. invalid price/volume)
             raise Exception(f"cTrader Order Error: {error.errorCode} - {error.description} (Order {error.orderId})")
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
        elif resp_msg.payloadType == ProtoOAOrderErrorEvent().payloadType:
             error = ProtoOAOrderErrorEvent()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Cancel Order Error (2132): {error.errorCode} - {error.description} (Order {error.orderId})")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def amend_order(self, account_id: int, order_id: int, 
                    volume: Optional[int] = None, 
                    price: Optional[float] = None, 
                    sl: Optional[float] = None, 
                    tp: Optional[float] = None):
        req = ProtoOAAmendOrderReq()
        req.ctidTraderAccountId = int(account_id)
        req.orderId = int(order_id)
        
        if volume is not None: req.volume = int(volume)
        if price is not None: req.limitPrice = float(price)
        if sl is not None: req.stopLoss = float(sl)
        if tp is not None: req.takeProfit = float(tp)
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOAExecutionEvent().payloadType:
            res = ProtoOAExecutionEvent()
            res.ParseFromString(resp_msg.payload)
            return res
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Amend Order Error: {error.errorCode} - {error.description}")
        elif resp_msg.payloadType == ProtoOAOrderErrorEvent().payloadType:
             error = ProtoOAOrderErrorEvent()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Amend Order Error: {error.errorCode} - {error.description} (Order {error.orderId})")
        else:
             raise Exception(f"Unexpected response type: {resp_msg.payloadType}")

    async def amend_position_sltp(self, account_id: int, position_id: int, 
                             sl: Optional[float] = None, 
                             tp: Optional[float] = None):
        req = ProtoOAAmendPositionSLTPReq()
        req.ctidTraderAccountId = int(account_id)
        req.positionId = int(position_id)
        
        if sl is not None: req.stopLoss = float(sl)
        if tp is not None: req.takeProfit = float(tp)
        
        resp_msg = await self.send(req)
        
        if resp_msg.payloadType == ProtoOAExecutionEvent().payloadType:
            res = ProtoOAExecutionEvent()
            res.ParseFromString(resp_msg.payload)
            return res
        elif resp_msg.payloadType == ProtoOAErrorRes().payloadType:
             error = ProtoOAErrorRes()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Amend Position Error: {error.errorCode} - {error.description}")
        elif resp_msg.payloadType == ProtoOAOrderErrorEvent().payloadType:
             error = ProtoOAOrderErrorEvent()
             error.ParseFromString(resp_msg.payload)
             raise Exception(f"Amend Position Error: {error.errorCode} - {error.description} (Position {error.positionId})")
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

    async def get_spot_price(self, account_id: int, symbol_id: int, timeout: float = 5.0) -> tuple[float, float]:
        """
        Fetch current BID/ASK spot price via one-shot subscribe→receive→unsubscribe.
        Returns (bid, ask) as floats. Prices are in 1/100000 of quote currency (pipette).
        
        Protocol pattern from OpenApiPy ConsoleSample:
        1. Send ProtoOASubscribeSpotsReq
        2. Receive ProtoOASpotEvent (unsolicited via message handler)
        3. Send ProtoOAUnsubscribeSpotsReq immediately after
        """
        # Create a one-shot Future to receive the spot event
        loop = asyncio.get_running_loop()
        spot_future: asyncio.Future = loop.create_future()

        original_handler = self._message_handler

        def _spot_handler(msg):
            if spot_future.done():
                return
            if msg.payloadType == ProtoOASpotEvent().payloadType:
                spot = ProtoOASpotEvent()
                spot.ParseFromString(msg.payload)
                if spot.symbolId == symbol_id:
                    # Prices are in pipettes (1/100000); divide by 100000.0
                    bid = spot.bid / 100000.0 if spot.bid else 0.0
                    ask = spot.ask / 100000.0 if spot.ask else bid
                    spot_future.set_result((bid, ask))
            elif original_handler:
                original_handler(msg)

        self._message_handler = _spot_handler

        try:
            # Subscribe to spot
            sub_req = ProtoOASubscribeSpotsReq()
            sub_req.ctidTraderAccountId = int(account_id)
            sub_req.symbolId.append(int(symbol_id))

            sub_resp_msg = await self.send(sub_req)
            if sub_resp_msg.payloadType == ProtoOAErrorRes().payloadType:
                error = ProtoOAErrorRes()
                error.ParseFromString(sub_resp_msg.payload)
                raise Exception(f"Subscribe Spots Error: {error.errorCode} - {error.description}")

            # Wait for spot event
            bid, ask = await asyncio.wait_for(spot_future, timeout=timeout)
            return bid, ask

        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for spot price for symbolId={symbol_id}")
            raise ValueError(f"Spot price timeout for symbolId={symbol_id}")
        finally:
            # Restore original message handler
            self._message_handler = original_handler
            # Always unsubscribe to free server resources
            try:
                unsub_req = ProtoOAUnsubscribeSpotsReq()
                unsub_req.ctidTraderAccountId = int(account_id)
                unsub_req.symbolId.append(int(symbol_id))
                await self._send_proto_message(
                    ProtoMessage(
                        payloadType=unsub_req.payloadType,
                        payload=unsub_req.SerializeToString()
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to unsubscribe spots for symbolId={symbol_id}: {e}")

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
    async def get_order_book(self, account_id: int, symbol_id: int, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Fetch current Depth of Market (Order Book) via one-shot subscribe→receive→unsubscribe.
        Returns a dict with 'bids' and 'asks' lists, each containing {'price': float, 'volume': float}.
        """
        loop = asyncio.get_running_loop()
        dom_future: asyncio.Future = loop.create_future()

        original_handler = self._message_handler

        def _dom_handler(msg):
            if dom_future.done():
                return
            if msg.payloadType == ProtoOADepthEvent().payloadType:
                event = ProtoOADepthEvent()
                event.ParseFromString(msg.payload)
                if event.symbolId == symbol_id:
                    bids = []
                    asks = []
                    # cTrader DepthEvent contains newQuotes (additions/initial snapshot)
                    for quote in event.newQuotes:
                        # Price is in pipettes (1/100000)
                        if quote.bid:
                            bids.append({"price": quote.bid / 100000.0, "volume": float(quote.size)})
                        if quote.ask:
                            asks.append({"price": quote.ask / 100000.0, "volume": float(quote.size)})
                    
                    if bids or asks:
                        # Sort bids descending, asks ascending
                        bids.sort(key=lambda x: x["price"], reverse=True)
                        asks.sort(key=lambda x: x["price"])
                        dom_future.set_result({"bids": bids, "asks": asks})
            elif original_handler:
                if asyncio.iscoroutinefunction(original_handler):
                    asyncio.create_task(original_handler(msg))
                else:
                    original_handler(msg)

        self._message_handler = _dom_handler

        try:
            # Subscribe to Depth Quotes
            sub_req = ProtoOASubscribeDepthQuotesReq()
            sub_req.ctidTraderAccountId = int(account_id)
            sub_req.symbolId.append(int(symbol_id))

            sub_resp_msg = await self.send(sub_req)
            if sub_resp_msg.payloadType == ProtoOAErrorRes().payloadType:
                error = ProtoOAErrorRes()
                error.ParseFromString(sub_resp_msg.payload)
                raise Exception(f"Subscribe Depth Quotes Error: {error.errorCode} - {error.description}")

            # Wait for Depth event
            book = await asyncio.wait_for(dom_future, timeout=timeout)
            return book

        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for Depth for symbolId={symbol_id}")
            raise ValueError(f"Depth timeout for symbolId={symbol_id}")
        finally:
            # Restore original message handler
            self._message_handler = original_handler
            # Unsubscribe
            try:
                unsub_req = ProtoOAUnsubscribeDepthQuotesReq()
                unsub_req.ctidTraderAccountId = int(account_id)
                unsub_req.symbolId.append(int(symbol_id))
                await self._send_proto_message(
                    ProtoMessage(
                        payloadType=unsub_req.payloadType,
                        payload=unsub_req.SerializeToString()
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to unsubscribe Depth for symbolId={symbol_id}: {e}")
