"""
Sprint I: WS Reconnection & Heartbeat Proof (R1-R5).
Standalone integration test that inlines the MTFWebSocketClient SDK.

Scenarios:
R1: Connection Drop -> Auto-reconnect
R2: Message Queue -> Buffer while down, replay on up
R3: Auth Persistence -> Refresh signature on reconnect
R4: Stress Test -> Rapid disconnect/reconnect
R5: Heartbeat -> Ping/Pong verification
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
import websockets
from typing import Any, Callable, Coroutine, Dict, List, Optional
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# ─── INLINED SDK ─────────────────────────────────────────────────────────────

class MTFWebSocketClient:
    MAX_BACKOFF = 30.0
    INITIAL_BACKOFF = 1.0

    def __init__(
        self,
        url: str,
        api_key: str,
        api_secret: str,
        allowed_commands: str = "execute,cancel,amend,close,get_account,get_orders,get_trades",
    ):
        self.base_url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.allowed_commands = allowed_commands
        self.on_message = None
        self.on_connect = None
        self.on_disconnect = None
        self.on_reconnect = None
        self._ws = None
        self._connected = False
        self._running = False
        self._reconnect_attempt = 0
        self._pending_queue = []
        self._lock = asyncio.Lock()

    def _sign(self, timestamp: str) -> str:
        payload = f"{timestamp}GET/api/v1/external/ws/command"
        return hmac.new(self.api_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def _build_url(self) -> str:
        ts = str(time.time())
        sig = self._sign(ts)
        return (f"{self.base_url}?api_key={self.api_key}&timestamp={ts}&signature={sig}&commands={self.allowed_commands}")

    async def connect(self) -> None:
        self._running = True
        asyncio.create_task(self._connection_loop())

    async def disconnect(self) -> None:
        self._running = False
        if self._ws: await self._ws.close()

    async def _connection_loop(self) -> None:
        while self._running:
            try:
                url = self._build_url()
                async with websockets.connect(url) as ws:
                    self._ws = ws
                    self._connected = True
                    if self._reconnect_attempt == 0 and self.on_connect: await self.on_connect()
                    elif self._reconnect_attempt > 0 and self.on_reconnect: await self.on_reconnect(self._reconnect_attempt)
                    self._reconnect_attempt = 0
                    await self._replay_pending()
                    await self._receive_loop(ws)
            except Exception: pass
            finally:
                self._connected = False
                self._ws = None
            if not self._running: break
            self._reconnect_attempt += 1
            backoff = min(self.INITIAL_BACKOFF * (2 ** (self._reconnect_attempt - 1)), self.MAX_BACKOFF)
            if self.on_disconnect: await self.on_disconnect(f"Reconnecting in {backoff:.0f}s")
            await asyncio.sleep(backoff)

    async def _receive_loop(self, ws) -> None:
        async for raw in ws:
            try: msg = json.loads(raw)
            except: continue
            if msg.get("type") == "ping":
                try: await ws.send(json.dumps({"type": "pong", "ts": msg.get("ts")}))
                except: break
                continue
            if self.on_message: await self.on_message(msg)

    async def send(self, cmd: str, params: Dict[str, Any], cmd_id: Optional[str] = None) -> str:
        if cmd_id is None: cmd_id = str(uuid.uuid4())
        message = {"cmd": cmd, "id": cmd_id, "params": params}
        if self._connected and self._ws:
            try:
                await self._ws.send(json.dumps(message))
                return cmd_id
            except: pass
        async with self._lock: self._pending_queue.append(message)
        return cmd_id

    async def _replay_pending(self) -> None:
        async with self._lock:
            if not self._pending_queue: return
            for message in self._pending_queue:
                try: await self._ws.send(json.dumps(message))
                except: break
            self._pending_queue.clear()

# ─── TESTS ───────────────────────────────────────────────────────────────────

# Mock URL and credentials
WS_URL = "ws://localhost:8000/api/v1/external/ws/command"
API_KEY = "test_api_key_12345"
API_SECRET = "test_secret_67890"

@pytest.fixture
def client():
    return MTFWebSocketClient(WS_URL, API_KEY, API_SECRET)

# ─── TESTS ───────────────────────────────────────────────────────────────────

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_ws")

WS_URL = "ws://localhost:8000/api/v1/external/ws/command"
API_KEY = "test_api_key_12345"
API_SECRET = "test_secret_67890"

class MockWS:
    def __init__(self, messages=None):
        self.messages = messages or []
        self.sent = []
        self.closed = False

    async def send(self, data):
        self.sent.append(json.loads(data))
        logger.info(f"MockWS sent: {data}")

    async def close(self, code=1000):
        self.closed = True

    def __aiter__(self):
        return self._iterator()

    async def _iterator(self):
        for m in self.messages:
            yield m
        # Hold the loop open until disconnected or sleep
        await asyncio.sleep(0.5)

class MockConnect:
    def __init__(self, ws, fail_count=0):
        self.ws = ws
        self.fail_count = fail_count
        self.current_fail = 0

    async def __aenter__(self):
        if self.current_fail < self.fail_count:
            self.current_fail += 1
            raise ConnectionError("Mock Fail")
        return self.ws

    async def __aexit__(self, *args):
        pass

@pytest.fixture
def client():
    c = MTFWebSocketClient(WS_URL, API_KEY, API_SECRET)
    c.INITIAL_BACKOFF = 0.001
    return c

@pytest.mark.asyncio
async def test_r1_r2_reconnect_and_replay(client):
    """R1: Reconnect, R2: Queue Replay."""
    mock_ws = MockWS(messages=[json.dumps({"type": "welcome"})])
    
    with patch("websockets.connect", side_effect=lambda url: MockConnect(mock_ws)):
        await client.connect()
        await asyncio.sleep(0.1)
        assert client._connected == True
        
        # Drop
        client._connected = False
        client._ws = None
        
        # Buffer (R2)
        cmd_id = await client.send("execute", {"symbol": "XAU_USD"})
        
        # Wait for Reconnect
        for _ in range(20):
            if client._connected and not client._pending_queue: break
            await asyncio.sleep(0.1)
        
        assert client._connected == True
        assert any(m.get("id") == cmd_id for m in mock_ws.sent)
        await client.disconnect()

@pytest.mark.asyncio
async def test_r3_auth_refresh_on_reconnect(client):
    """R3: Refresh HMAC signature."""
    urls = []
    def mock_connect(url):
        urls.append(url)
        class Fail:
            async def __aenter__(self): raise ConnectionError("Fail")
            async def __aexit__(self, *args): pass
        return Fail()

    with patch("websockets.connect", side_effect=mock_connect):
        client._running = True
        task = asyncio.create_task(client._connection_loop())
        await asyncio.sleep(0.1)
        client._running = False
        try: await asyncio.wait_for(task, timeout=0.2)
        except: pass

    assert len(urls) >= 2
    ts1 = urls[0].split("timestamp=")[1].split("&")[0]
    ts2 = urls[1].split("timestamp=")[1].split("&")[0]
    assert ts1 != ts2

@pytest.mark.asyncio
async def test_r4_rapid_disconnect_recovery(client):
    """R4: Stress recovery."""
    mock_ws = MockWS()
    # Fails 2 times then success
    conn_mock = MockConnect(mock_ws, fail_count=2)

    with patch("websockets.connect", return_value=conn_mock):
        await client.connect()
        for _ in range(10):
            if client._connected: break
            await asyncio.sleep(0.05)
        assert client._connected == True
        await client.disconnect()

@pytest.mark.asyncio
async def test_r5_heartbeat_pong(client):
    """R5: Heartbeat Ping/Pong."""
    mock_ws = MockWS(messages=[json.dumps({"type": "ping", "ts": 555.5})])
    
    with patch("websockets.connect", side_effect=lambda url: MockConnect(mock_ws)):
        await client.connect()
        await asyncio.sleep(0.2)
        assert any(m.get("type") == "pong" and m.get("ts") == 555.5 for m in mock_ws.sent)
        await client.disconnect()
