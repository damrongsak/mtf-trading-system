"""
G5: MTF Olympus WebSocket Client — Reference Implementation
Bloomberg API-style auto-reconnect with exponential backoff.

Quick Start:
    import asyncio
    from mtf_ws_client import MTFWebSocketClient

    async def on_msg(data):
        print("Received:", data)

    async def main():
        client = MTFWebSocketClient(
            url="ws://localhost:8000/api/v1/external/ws/command",
            api_key="your_api_key",
            api_secret="your_hmac_secret",
            allowed_commands="execute,amend,close,get_account"
        )
        client.on_message = on_msg
        async with client:
            await client.send("get_account", {"broker_account_id": "12345"})
            await asyncio.sleep(60)

    asyncio.run(main())

Environment:
    pip install websockets
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class MTFWebSocketClient:
    """
    Bloomberg API-style WebSocket client with:
    - Auto-reconnect with exponential backoff (1s → 2s → 4s → max 30s)
    - HMAC-SHA256 re-authentication on every reconnect
    - Command queue: buffers unsent commands during disconnect, replays on reconnect
    - Pong response to server heartbeats (G1 compatibility)
    - Callbacks: on_message, on_connect, on_disconnect, on_reconnect
    """

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

        # Callbacks (assign before connecting)
        self.on_message: Optional[Callable[[Dict], Coroutine]] = None
        self.on_connect: Optional[Callable[[], Coroutine]] = None
        self.on_disconnect: Optional[Callable[[str], Coroutine]] = None
        self.on_reconnect: Optional[Callable[[int], Coroutine]] = None

        # Internal state
        self._ws = None
        self._connected = False
        self._running = False
        self._reconnect_attempt = 0
        self._pending_queue: List[Dict] = []  # Commands buffered during disconnect
        self._lock = asyncio.Lock()

    # ── Authentication ────────────────────────────────────────────────────────

    def _sign(self, timestamp: str) -> str:
        """Generate HMAC-SHA256 signature for WebSocket authentication."""
        payload = f"{timestamp}GET/api/v1/external/ws/command"
        return hmac.new(
            self.api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _build_url(self) -> str:
        """Build authenticated WebSocket URL with HMAC query params."""
        ts = str(time.time())
        sig = self._sign(ts)
        return (
            f"{self.base_url}"
            f"?api_key={self.api_key}"
            f"&timestamp={ts}"
            f"&signature={sig}"
            f"&commands={self.allowed_commands}"
        )

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(self) -> None:
        """Connect and start the receive loop. This does not block."""
        self._running = True
        asyncio.create_task(self._connection_loop())

    async def disconnect(self) -> None:
        """Gracefully disconnect and stop reconnecting."""
        self._running = False
        if self._ws:
            await self._ws.close()

    async def __aenter__(self):
        await self.connect()
        # Wait for initial connection
        for _ in range(50):
            if self._connected:
                break
            await asyncio.sleep(0.1)
        return self

    async def __aexit__(self, *args):
        await self.disconnect()

    # ── Core connection loop with backoff ─────────────────────────────────────

    async def _connection_loop(self) -> None:
        """Main reconnect loop with exponential backoff."""
        try:
            import websockets
        except ImportError:
            logger.error("[G5] 'websockets' library not installed. Run: pip install websockets")
            return

        while self._running:
            try:
                url = self._build_url()
                async with websockets.connect(url) as ws:
                    self._ws = ws
                    self._connected = True
                    self._reconnect_attempt = 0

                    if self._reconnect_attempt == 0 and self.on_connect:
                        await self.on_connect()
                    elif self._reconnect_attempt > 0 and self.on_reconnect:
                        await self.on_reconnect(self._reconnect_attempt)

                    # Replay buffered commands after reconnect
                    await self._replay_pending()

                    await self._receive_loop(ws)

            except Exception as e:
                reason = f"{type(e).__name__}: {e}"
                logger.warning(f"[G5] WS disconnected: {reason}")

            finally:
                self._connected = False
                self._ws = None

            if not self._running:
                break

            # Exponential backoff
            self._reconnect_attempt += 1
            backoff = min(self.INITIAL_BACKOFF * (2 ** (self._reconnect_attempt - 1)), self.MAX_BACKOFF)
            logger.info(f"[G5] Reconnect attempt {self._reconnect_attempt} in {backoff:.1f}s...")

            if self.on_disconnect:
                try:
                    await self.on_disconnect(f"Reconnecting in {backoff:.0f}s")
                except Exception:
                    pass

            await asyncio.sleep(backoff)

    # ── Receive loop ──────────────────────────────────────────────────────────

    async def _receive_loop(self, ws) -> None:
        """Receive messages and dispatch to callbacks. Handle server pings (G1)."""
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"[G5] Non-JSON message received: {raw[:100]}")
                continue

            # [G1] Respond to server heartbeat pings
            if msg.get("type") == "ping":
                try:
                    await ws.send(json.dumps({"type": "pong", "ts": msg.get("ts")}))
                except Exception:
                    break
                continue

            # Dispatch to user callback
            if self.on_message:
                try:
                    await self.on_message(msg)
                except Exception as e:
                    logger.error(f"[G5] on_message callback error: {e}")

    # ── Send API ──────────────────────────────────────────────────────────────

    async def send(self, cmd: str, params: Dict[str, Any], cmd_id: Optional[str] = None) -> str:
        """
        Send a WebSocket command.
        
        If not connected, the command is buffered and sent after reconnect.
        Returns the command ID (trace_id) for correlation.

        Args:
            cmd:     Command name (e.g., 'execute', 'get_account')
            params:  Command parameters dict
            cmd_id:  Optional unique ID (auto-generated UUID4 if not provided)

        Returns:
            cmd_id: The command ID / trace_id for this request
        """
        if cmd_id is None:
            cmd_id = str(uuid.uuid4())

        message = {"cmd": cmd, "id": cmd_id, "params": params}

        if self._connected and self._ws:
            try:
                await self._ws.send(json.dumps(message))
                return cmd_id
            except Exception as e:
                logger.warning(f"[G5] Send failed ({e}), buffering command {cmd_id}")

        # Buffer command for replay after reconnect
        async with self._lock:
            self._pending_queue.append(message)
            logger.info(f"[G5] Command '{cmd}' buffered (queue size: {len(self._pending_queue)})")

        return cmd_id

    async def _replay_pending(self) -> None:
        """Replay buffered commands after reconnect."""
        async with self._lock:
            if not self._pending_queue:
                return
            logger.info(f"[G5] Replaying {len(self._pending_queue)} buffered commands...")
            for message in self._pending_queue:
                try:
                    await self._ws.send(json.dumps(message))
                    await asyncio.sleep(0.01)  # Small delay between replayed commands
                except Exception as e:
                    logger.error(f"[G5] Failed to replay command {message.get('id')}: {e}")
            self._pending_queue.clear()
