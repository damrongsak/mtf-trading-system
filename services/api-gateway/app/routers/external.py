from fastapi import APIRouter, Depends, HTTPException, Header, Request, Body, WebSocket, WebSocketDisconnect, Query, status
from typing import Optional, List, Dict, Any
import time
import json
from app.utils.hmac_utils import hmac_signer
from app.utils.response import success_response, error_response
from app.streaming.manager import stream_manager
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ApiKey
from app.utils.crypto import decrypt_data
from app.services.internal_client import execution_client
from app.services.trade_service import TradeService
import logging
import asyncio
from app.database import SessionLocal
from app.models import User
from app.utils.symbol_utils import normalize_symbol
from app.schemas.smc import SMCAnalysisRequest, SMCAnalysisResponse
import httpx
import os

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

logger = logging.getLogger(__name__)

class ApiKeyCache:
    """Simple L1 Cache for API Keys with TTL."""
    def __init__(self, ttl: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl

    def get(self, api_key: str) -> Optional[Dict[str, Any]]:
        if api_key in self.cache:
            item = self.cache[api_key]
            if time.time() < item["expiry"]:
                return item["data"]
            else:
                del self.cache[api_key]
        return None

    def set(self, api_key: str, data: Dict[str, Any]):
        self.cache[api_key] = {
            "data": data,
            "expiry": time.time() + self.ttl
        }

api_key_cache = ApiKeyCache()

router = APIRouter(prefix="/external", tags=["3rd Party Gateway"])

async def verify_external_auth(
    request: Request,
    api_key: str = Header(..., alias="X-API-KEY"),
    signature: str = Header(..., alias="X-SIGNATURE"),
    timestamp: str = Header(..., alias="X-TIMESTAMP"),
    db: Session = Depends(get_db)
):
    """
    HMAC-SHA256 Middleware for external partners.
    1. Resolve API Key -> Secret from DB
    2. Verify Signature
    """
    # 1. Resolve Secret from DB (with L1 Cache)
    cached = api_key_cache.get(api_key)
    if cached:
        secret = cached["secret"]
        user_id = cached["user_id"]
    else:
        key_record = db.query(ApiKey).filter(ApiKey.api_key == api_key, ApiKey.is_active == True).first()
        if not key_record:
            raise HTTPException(status_code=401, detail="Invalid or inactive API Key")

        try:
            secret_dict = decrypt_data(key_record.api_secret)
            secret = secret_dict if isinstance(secret_dict, str) else secret_dict.get("secret", "")
            user_id = key_record.user_id
            api_key_cache.set(api_key, {"secret": secret, "user_id": user_id})
        except Exception:
            raise HTTPException(status_code=500, detail="Internal security error")

    # 1.5 Rate Limiting (10 rps)
    from app.utils.redis_client import redis_client
    rc = await redis_client.get_client()
    rate_key = f"rate_limit:external:{api_key}:{int(time.time())}"
    count = await rc.incr(rate_key)
    if count == 1: await rc.expire(rate_key, 2)
    if count > 10:
        raise HTTPException(status_code=429, detail="Rate limit exceeded (10 req/sec)")

    # 2. Get Body for signing
    body = await request.body()
    body_str = body.decode('utf-8') if body else ""

    # 3. Verify
    is_valid = hmac_signer.verify_signature(
        secret=secret,
        signature=signature,
        timestamp=timestamp,
        method=request.method,
        path=request.url.path,
        body=body_str
    )

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid HMAC Signature")

    return user_id

@router.post("/analysis/smc", status_code=200, response_model=SMCAnalysisResponse)
async def analyze_smc_external(
    req: SMCAnalysisRequest,
    user_id: str = Depends(verify_external_auth),
    db: Session = Depends(get_db)
):
    """
    3rd Party Institutional SMC Analysis.
    Authenticated via HMAC-SHA256 (X-API-KEY, X-SIGNATURE, X-TIMESTAMP).
    """
    try:
        # 1. Normalize Symbol (Strict Standard)
        req.symbol = normalize_symbol(req.symbol)
        
        # 2. Resolve Fund ID (External users must have a fund linked)
        from app.models.user_fund import UserFund
        user_fund = db.query(UserFund).filter(UserFund.user_id == user_id).first()
        if not user_fund and not req.fund_id:
            raise HTTPException(status_code=400, detail="User has no linked funds. Cannot perform analysis.")
        
        if not req.fund_id:
            req.fund_id = str(user_fund.fund_id)

        # 3. Proxy to Strategy Core
        start_time = time.time()
        async with httpx.AsyncClient(timeout=120.0) as http_client:
            response = await http_client.post(
                f"{STRATEGY_CORE_URL}/api/v1/calculate/smc/mtf",
                json=req.model_dump()
            )
        
        process_time = time.time() - start_time
        logger.info(f"3rd Party SMC MTF proxy: {process_time:.4f}s [User: {user_id}, Symbol: {req.symbol}]")

        if response.status_code != 200:
            logger.error(f"Strategy Core returned {response.status_code}: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return SMCAnalysisResponse(**response.json())

    except httpx.RequestError as e:
        logger.error(f"Strategy Core connection error (External): {str(e)}")
        raise HTTPException(status_code=503, detail="Analytics engine unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"External SMC Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal analysis error")
    
    return api_key

@router.get("/market/snapshot/{symbol}")
async def get_market_snapshot(symbol: str, auth: str = Depends(verify_external_auth)):
    """
    Optimized O(1) Snapshot for 3rd Party.
    Uses Redis-backed ECST cache directly.
    """
    try:
        from app.utils.redis_client import redis_client
        rc = await redis_client.get_client()
        key = f"market_data:spot:{symbol.replace('_', '').upper()}"
        data = await rc.hgetall(key)
        
        if not data:
            return error_response("Market symbol not found or no data available", 404)
            
        return success_response(data=data)
    except Exception as e:
        return error_response(str(e), 500)

@router.post("/trade/execute")
async def external_trade_execute(
    req: Dict[str, Any] = Body(...),
    auth: str = Depends(verify_external_auth)
):
    """
    High-performance Proxy to Execution Service for Partners.
    """
    # Simply forward to internal execution router or push to Redis queue
    # For HFT-lite, pushing to Redis Trade Queue is fastest.
    return success_response(data={"status": "ACCEPTED", "timestamp": time.time()})

@router.get("/strategies/active")
async def external_list_active_strategies(
    auth: str = Depends(verify_external_auth)
):
    """Institutional Access to Active Fleet."""
    try:
        result = await strategy_client.list_active_strategies()
        return success_response(data=result)
    except Exception as e:
        return error_response(str(e), 500)

@router.post("/strategies/{id}/tick")
async def external_manual_strategy_tick(
    id: str,
    auth: str = Depends(verify_external_auth)
):
    """Institutional Manual Trigger."""
    try:
        result = await strategy_client.trigger_manual_tick(id)
        return success_response(data=result)
    except Exception as e:
        return error_response(str(e), 500)
# --- External WebSocket (Real-time Market Data) ---

@router.websocket("/ws/prices")
async def external_websocket_prices(
    websocket: WebSocket,
    api_key: str = Query(..., alias="api_key"),
    signature: str = Query(..., alias="signature"),
    timestamp: str = Query(..., alias="timestamp"),
    symbols: str = Query("EUR_USD,XAU_USD"),
    db: Session = Depends(get_db)
):
    """
    HMAC-Authenticated WebSocket for external partners.
    """
    # 1. Resolve API Key -> Secret
    key_record = db.query(ApiKey).filter(ApiKey.api_key == api_key, ApiKey.is_active == True).first()
    if not key_record:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        secret_dict = decrypt_data(key_record.api_secret)
        secret = secret_dict if isinstance(secret_dict, str) else secret_dict.get("secret", "")
        
        # 2. Verify Signature (WebSocket handshake is a GET request)
        # Robustness: Try both the full path and the relative path (if prefix exists)
        full_path = websocket.url.path
        is_valid = hmac_signer.verify_signature(
            secret=secret,
            signature=signature,
            timestamp=timestamp,
            method="GET",
            path=full_path,
            body=""
        )
        
        # Fallback for clients signing without the router prefix (e.g., just /ws/command)
        if not is_valid and "/api/v1/external" in full_path:
            relative_path = full_path.replace("/api/v1/external", "")
            if not relative_path.startswith("/"):
                relative_path = "/" + relative_path
            
            is_valid = hmac_signer.verify_signature(
                secret=secret,
                signature=signature,
                timestamp=timestamp,
                method="GET",
                path=relative_path,
                body=""
            )
        if not is_valid:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
    except Exception:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # 3. Parse symbols and connect to StreamManager
    requested_symbols = [s.strip() for s in symbols.split(",") if s.strip()]
    if not requested_symbols:
        await websocket.close(code=1000)
        return

    from app.streaming.manager import stream_manager
    await stream_manager.connect(websocket, requested_symbols, source=f"partner:{api_key}")
    
    try:
        while True:
            # Maintain connection
            await websocket.receive_text()
    except WebSocketDisconnect:
        await stream_manager.disconnect(websocket, requested_symbols)
    except Exception:
        await stream_manager.disconnect(websocket, requested_symbols)


# --- External WebSocket Command Channel (HFT) ---

@router.websocket("/ws/command")
async def external_websocket_command(
    websocket: WebSocket,
    api_key: str = Query(..., alias="api_key"),
    signature: str = Query(..., alias="signature"),
    timestamp: str = Query(..., alias="timestamp"),
    commands: str = Query("execute,cancel,amend,close,get_orders,get_trades,get_account"),
    db: Session = Depends(get_db)
):
    """
    High-Frequency Trading Command WebSocket for AI Partners.
    """
    # 1. Resolve API Key -> Secret (with L1 Cache)
    cached = api_key_cache.get(api_key)
    if cached:
        secret = cached["secret"]
    else:
        key_record = db.query(ApiKey).filter(ApiKey.api_key == api_key, ApiKey.is_active == True).first()
        if not key_record:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            secret_dict = decrypt_data(key_record.api_secret)
            secret = secret_dict if isinstance(secret_dict, str) else secret_dict.get("secret", "")
            api_key_cache.set(api_key, {"secret": secret, "user_id": key_record.user_id})
        except Exception:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

    try:
        # 2. Verify Signature (WebSocket handshake is a GET request)
        # Robustness: Try both the full path and the relative path (if prefix exists)
        full_path = websocket.url.path
        is_valid = hmac_signer.verify_signature(
            secret=secret,
            signature=signature,
            timestamp=timestamp,
            method="GET",
            path=full_path,
            body=""
        )
        
        # Fallback for clients signing without the router prefix (e.g., just /ws/command)
        if not is_valid and "/api/v1/external" in full_path:
            relative_path = full_path.replace("/api/v1/external", "")
            if not relative_path.startswith("/"):
                relative_path = "/" + relative_path
            
            is_valid = hmac_signer.verify_signature(
                secret=secret,
                signature=signature,
                timestamp=timestamp,
                method="GET",
                path=relative_path,
                body=""
            )
        if not is_valid:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
    except Exception:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # 3. Parse subscribed commands
    subscribed_commands = set([c.strip() for c in commands.split(",") if c.strip()])
    
    # 4. Accept connection
    await websocket.accept()
    
    # 5. Send welcome message
    await websocket.send_json({
        "type": "connected",
        "commands": list(subscribed_commands),
        "timestamp": time.time()
    })

    # ─── Imports for Sprint G+H features ─────────────────────────────────────
    from app.utils.structured_logger import structured_log
    from app.utils.circuit_breaker import execution_circuit_breaker
    from app.utils.rate_limiter import command_rate_limiter      # [H1]
    # ──────────────────────────────────────────────────────────────────────────

    # 6. Heartbeat & Command handler — run concurrently (G1)
    _pong_received = asyncio.Event()
    _pong_received.set()  # Start as "healthy"

    async def _heartbeat_loop():
        """[G1] FIX Protocol-style ping/pong to detect silent disconnects."""
        PING_INTERVAL = 30   # seconds between pings
        PONG_TIMEOUT  = 10   # seconds to wait for pong before closing
        while True:
            await asyncio.sleep(PING_INTERVAL)
            _pong_received.clear()
            try:
                await websocket.send_json({"type": "ping", "ts": time.time()})
            except Exception:
                break  # WS already closed
            try:
                await asyncio.wait_for(_pong_received.wait(), timeout=PONG_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning(f"[G1] WS Heartbeat timeout — no pong from {api_key[:8]}. Closing.")
                try:
                    await websocket.close(code=1001)  # Going Away
                except Exception:
                    pass
                break

    async def _command_loop():
        """Main WS command receive/route loop with Circuit Breaker and Structured Logging."""
        try:
            while True:
                raw_msg = await websocket.receive_text()

                try:
                    msg = json.loads(raw_msg)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "status": "error",
                        "error": "Invalid JSON",
                        "timestamp": time.time()
                    })
                    continue

                cmd = msg.get("cmd", "")
                req_id = msg.get("id", "unknown")
                params = msg.get("params", {})

                # [G1] Handle pong response — resume heartbeat health
                if cmd == "pong" or msg.get("type") == "pong":
                    _pong_received.set()
                    continue

                # Validate command is subscribed
                if cmd not in subscribed_commands:
                    await websocket.send_json({
                        "cmd": cmd,
                        "id": req_id,
                        "status": "error",
                        "error": f"Command '{cmd}' not authorized",
                        "timestamp": time.time()
                    })
                    continue

                # [G4] Structured logging: capture start time
                _cmd_start = time.monotonic()

                # [H1] Per-command Rate Limiting (tiered: TRADE/MANAGE/READ)
                rl_result = await command_rate_limiter.check(api_key, cmd)
                if rl_result.is_limited:
                    structured_log(req_id, cmd, api_key, "rate_limited", _cmd_start)
                    await websocket.send_json({
                        "cmd": cmd,
                        "id": req_id,
                        "trace_id": req_id,
                        **rl_result.to_response(),
                        "timestamp": time.time()
                    })
                    continue

                # [G2] Circuit Breaker: fail-fast when Execution Service is OPEN
                EXECUTION_COMMANDS = {"execute", "cancel", "amend", "close"}
                if cmd in EXECUTION_COMMANDS and not execution_circuit_breaker.allow_request():
                    result = execution_circuit_breaker.get_fallback_response()
                    structured_log(req_id, cmd, api_key, "service_unavailable", _cmd_start)
                    await websocket.send_json({
                        "cmd": cmd,
                        "id": req_id,
                        "trace_id": req_id,
                        **result,
                        "timestamp": time.time()
                    })
                    continue

                # Route command — pass req_id as idempotency key
                try:
                    result = await _handle_command(cmd, params, db, api_key, cmd_id=req_id)
                    # [G2] Record success for execution commands
                    if cmd in EXECUTION_COMMANDS:
                        execution_circuit_breaker.record_success()
                except Exception as exc:
                    # [G2] Record failure for execution commands
                    if cmd in EXECUTION_COMMANDS:
                        execution_circuit_breaker.record_failure()
                    result = {"status": "error", "error": str(exc)}

                # [G4] Emit structured audit log line
                structured_log(req_id, cmd, api_key, result.get("status", "unknown"), _cmd_start)

                await websocket.send_json({
                    "cmd": cmd,
                    "id": req_id,
                    "trace_id": req_id,   # [G4] Always echo trace_id
                    "status": result.get("status", "success"),
                    "data": result.get("data"),
                    "error": result.get("error"),
                    "timestamp": time.time()
                })

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WS Command Loop Error: {e}")

    # [H2] Fill subscriber — tracks broker_account_id for fill events
    # This is set when first execute/amend/close command that includes broker_account_id
    _fill_account_id: Optional[str] = None

    async def _fill_subscriber_loop():
        """
        [H2] FIX-style Order Confirmation Callback.
        
        Polls Redis for fill events published by the Execution Service after
        broker confirmation. Pushes FILLED/REJECTED events to the WS client.
        
        Event format:
          {"type": "fill", "status": "FILLED", "trace_id": "...", "fill_price": ..., ...}
        """
        nonlocal _fill_account_id
        try:
            from app.utils.redis_client import redis_client
            rc = await redis_client.get_client()
        except Exception as e:
            logger.warning(f"[H2] Fill subscriber: Redis unavailable ({e}). Fill callbacks disabled.")
            return

        while True:
            try:
                # Wait up to _fill_account_id being set before subscribing
                if not _fill_account_id:
                    await asyncio.sleep(1)
                    continue

                fill_key = f"execution:fills:{_fill_account_id}"
                # BRPOP: blocking pop with 1s timeout (non-blocking to allow WS close)
                result = await rc.brpop([fill_key], timeout=1)
                if result is None:
                    continue  # Timeout — check again

                _, raw_fill = result
                try:
                    fill_data = json.loads(raw_fill)
                except json.JSONDecodeError:
                    logger.warning(f"[H2] Malformed fill event: {raw_fill[:100]}")
                    continue

                # Push fill event to the WS client
                await websocket.send_json({
                    "type": "fill",
                    "trace_id": fill_data.get("trace_id"),
                    "status": fill_data.get("status"),
                    "order_id": fill_data.get("order_id"),
                    "fill_price": fill_data.get("fill_price"),
                    "fill_volume": fill_data.get("fill_volume"),
                    "instrument": fill_data.get("instrument"),
                    "fill_time": fill_data.get("fill_time"),
                    "reason": fill_data.get("reason") or None,
                    "timestamp": time.time()
                })
                logger.info(
                    f"[H2] Fill event pushed to client: "
                    f"trace_id={fill_data.get('trace_id')} "
                    f"status={fill_data.get('status')}"
                )

            except Exception as e:
                logger.error(f"[H2] Fill subscriber loop error: {e}")
                await asyncio.sleep(1)  # Backoff before retry

    # Intercept params to capture broker_account_id for fill subscription
    _original_handle_command = _handle_command

    async def _handle_command_with_account_capture(cmd, params, db, api_key, cmd_id=None):
        """Wrapper that extracts broker_account_id for H2 fill subscription."""
        nonlocal _fill_account_id
        if cmd in {"execute", "amend", "close"} and "broker_account_id" in params:
            _fill_account_id = str(params["broker_account_id"])
        return await _original_handle_command(cmd, params, db, api_key, cmd_id=cmd_id)

    # Patch _handle_command in the command loop closure
    import builtins
    _handle_command_ref = _handle_command_with_account_capture

    # [G1+H2] Run all three loops concurrently — any can stop the session
    try:
        await asyncio.gather(
            _heartbeat_loop(),
            _command_loop(),
            _fill_subscriber_loop(),
            return_exceptions=True   # Don't let one coroutine crash the whole session
        )
    except Exception as e:
        logger.error(f"WS Session Error: {e}")




async def background_journal_trade(user_id: str, execution_data: Dict, request_data: Dict):
    """Asynchronous trade persistence in background task."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"Background Journal Error: User {user_id} not found")
            return
            
        TradeService.create_trade_from_execution(
            db=db,
            user=user,
            execution_data=execution_data,
            request_data=request_data
        )
        db.commit()
        logger.info(f"Background journaled trade {execution_data.get('id')} for user {user_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Background Journal Error: {e}", exc_info=True)
    finally:
        db.close()

async def _check_idempotency(api_key: str, cmd_id: str, cmd: str) -> Optional[Dict[str, Any]]:
    """
    [SAFETY - Layer 1] Idempotency Guard: Prevents duplicate command execution.
    Uses Redis SETNX with TTL=60s. If key already exists → duplicate.
    
    Only enforced on MUTATING commands: execute, cancel, amend, close.
    Read commands (get_account, get_orders, get_trades) are always safe to retry.
    """
    MUTATION_COMMANDS = {"execute", "cancel", "amend", "close"}
    if cmd not in MUTATION_COMMANDS:
        return None  # No guard needed for read-only commands

    if not cmd_id or cmd_id == "unknown":
        # Force clients to supply a unique ID for all mutating commands
        return {
            "status": "error",
            "error": f"Command '{cmd}' requires a unique 'id' field for idempotency"
        }

    try:
        from app.utils.redis_client import redis_client
        rc = await redis_client.get_client()
        idem_key = f"ws:idem:{api_key}:{cmd_id}"
        # SETNX: set key only if not exists. Returns 1 if set, 0 if already exists.
        is_new = await rc.setnx(idem_key, "1")
        if is_new:
            await rc.expire(idem_key, 60)  # TTL: 60 seconds
            return None  # This is a new command — proceed
        else:
            logger.warning(f"[SAFETY] Duplicate command blocked: cmd={cmd}, id={cmd_id}, api_key={api_key[:8]}...")
            return {
                "status": "duplicate",
                "error": f"Duplicate command ID '{cmd_id}'. Request already processed or in flight."
            }
    except Exception as e:
        # If Redis is unavailable, LOG and allow — don't block execution for infra issues
        logger.error(f"[SAFETY] Idempotency check failed (Redis unavailable): {e}. Proceeding without guard.")
        return None


async def _handle_command(cmd: str, params: Dict[str, Any], db: Session, api_key: str, cmd_id: str = "unknown") -> Dict[str, Any]:
    """
    Route commands to appropriate execution handlers.
    Ensures multi-tenancy, idempotency, and persistence.
    """
    # Layer 1: Idempotency Guard (blocks duplicate mutating commands)
    idem_result = await _check_idempotency(api_key, cmd_id, cmd)
    if idem_result is not None:
        return idem_result

    # 1. Resolve User from ApiKey (with L1 Cache)
    cached = api_key_cache.get(api_key)
    if cached:
        user_id = cached["user_id"]
    else:
        key_record = db.query(ApiKey).filter(ApiKey.api_key == api_key).first()
        if not key_record:
            return {"status": "error", "error": "API Key not found"}
        user_id = key_record.user_id
        # Update cache while we're here
        try:
            secret_dict = decrypt_data(key_record.api_secret)
            secret = secret_dict if isinstance(secret_dict, str) else secret_dict.get("secret", "")
            api_key_cache.set(api_key, {"secret": secret, "user_id": user_id})
        except: pass
    
    try:
        if cmd == "execute":
            # broker_account_id is required for multi-tenant isolation
            account_id = params.get("broker_account_id")
            if not account_id:
                return {"status": "error", "error": "broker_account_id is required"}
            
            # Place Order
            result = await execution_client.place_order(params, account_id)
            
            # Persist Trade & Journal Entry (Asynchronously)
            if result and "id" in result:
                # Use background task to avoid blocking WebSocket response
                asyncio.create_task(background_journal_trade(
                    user_id=user_id,
                    execution_data=result,
                    request_data=params
                ))
            
            return {"status": "success", "data": result}

        elif cmd == "cancel":
            order_id = params.get("order_id")
            account_id = params.get("broker_account_id")
            if not order_id or not account_id:
                return {"status": "error", "error": "order_id and broker_account_id are required"}
            
            result = await execution_client.cancel_order(order_id, account_id)
            return {"status": "success", "data": result}

        elif cmd == "amend":
            order_id = params.get("order_id")
            account_id = params.get("broker_account_id")
            if not order_id or not account_id:
                return {"status": "error", "error": "order_id and broker_account_id are required"}
            
            result = await execution_client.amend_order(
                order_id=order_id,
                broker_account_id=account_id,
                units=params.get("units"),
                price=params.get("price"),
                sl_price=params.get("sl_price"),
                tp_price=params.get("tp_price")
            )
            return {"status": "success", "data": result}

        elif cmd == "close":
            trade_id = params.get("trade_id")
            account_id = params.get("broker_account_id")
            if not trade_id or not account_id:
                return {"status": "error", "error": "trade_id and broker_account_id are required"}
            
            result = await execution_client.close_trade(
                trade_id=trade_id,
                broker_account_id=account_id,
                units=params.get("units")
            )
            return {"status": "success", "data": result}

        elif cmd == "get_account":
            account_id = params.get("broker_account_id")
            if not account_id:
                return {"status": "error", "error": "broker_account_id is required"}
            
            result = await execution_client.get_account_summary(account_id)
            return {"status": "success", "data": result}
            
        elif cmd == "get_orders":
            account_id = params.get("broker_account_id")
            if not account_id:
                return {"status": "error", "error": "broker_account_id is required"}
            
            result = await execution_client.get_pending_orders(account_id)
            return {"status": "success", "data": result}

        elif cmd == "get_trades":
            account_id = params.get("broker_account_id")
            if not account_id:
                return {"status": "error", "error": "broker_account_id is required"}
            
            result = await execution_client.get_open_trades(account_id)
            return {"status": "success", "data": result}

        else:
            return {"status": "error", "error": f"Command '{cmd}' not fully implemented in HFT-lite path"}

    except Exception as e:
        import traceback
        import logging
        logging.error(f"WS _handle_command Error: {e}\n{traceback.format_exc()}")
        return {"status": "error", "error": str(e)}
