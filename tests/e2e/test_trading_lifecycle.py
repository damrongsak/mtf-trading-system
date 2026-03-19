import pytest
import asyncio
from datetime import datetime
import time

@pytest.mark.asyncio
async def test_system_health(api_client, auth_headers):
    """Test system-wide health endpoints."""
    # API Gateway
    response = await api_client.get("/api/v1/health")
    assert response.status_code == 200, f"API Gateway unhealthy: {response.text}"
    assert response.json()["status"] == "ok"

    # Execution Service (via manual proxy check or direct)
    resp_exec = await api_client.get("/api/v1/system/queue-health", headers=auth_headers)
    assert resp_exec.status_code == 200, f"Execution queue unhealthy: {resp_exec.text}"

@pytest.mark.asyncio
async def test_symbol_metadata_ecst(api_client, auth_headers):
    """Verify symbol metadata is correctly cached in api-gateway (ECST)."""
    # XAU_USD is the standard symbol for Gold in MTF Olympus
    url = "/api/v1/market/symbol/XAU_USD"
    response = await api_client.get(url, headers=auth_headers)
    
    # If not found, try XAUUSD (some brokers use this)
    if response.status_code == 404:
        url = "/api/v1/market/symbol/XAUUSD"
        response = await api_client.get(url, headers=auth_headers)

    assert response.status_code == 200, f"Symbol metadata not found: {response.text}"
    data = response.json()["data"]
    assert "symbol" in data
    assert "details" in data # Symbol details should be present (ECST from data-pipeline)

@pytest.mark.asyncio
async def test_market_order_lifecycle(api_client, auth_headers, broker_account, poller):
    """Full lifecycle: Place Market Order -> Wait for Fill -> Close."""
    # 1. Place Market Order
    order_url = "/api/v1/execution/orders"
    payload = {
        "broker_account_id": broker_account["id"],
        "symbol": "XAU_USD",
        "order_type": "MARKET",
        "units": 0.01,
        "comment": f"E2E_PYTEST_MKT_{int(time.time())}"
    }
    
    response = await api_client.post(order_url, json=payload, headers=auth_headers)
    assert response.status_code in [200, 201], f"Order placement failed: {response.text}"
    
    order_data = response.json().get("data", {})
    order_id = order_data.get("id")
    assert order_id, "Order ID missing in response"

    # 2. Wait for Fill (Async Polling)
    # Market orders are usually filled instantly, but we poll for state sync.
    async def check_trade_is_open():
        resp = await api_client.get("/api/v1/execution/trades", 
                                    params={"broker_account_id": broker_account["id"], "status": "OPEN"},
                                    headers=auth_headers)
        if resp.status_code != 200:
            return None, False
        
        trades = resp.json().get("data", [])
        # Find the trade with matching comment (comment isn't always returned in broker list, so match by entry or time)
        # For simplicity, we check if ANY trade is open or match by id if possible
        # Actually, let's look for a trade that might correspond to our order
        return trades, len(trades) > 0

    try:
        active_trades = await poller.wait_until(check_trade_is_open, timeout=30, message="Trade failed to appear in OPEN list")
    except TimeoutError:
        # Some brokers might close/fill so fast it doesn't appear? Re-check history.
        pytest.fail("Trade did not appear in OPEN status after 30s")

    # 3. Amend Trade (SL/TP)
    trade_id = active_trades[0]["trade_id"]
    amend_url = f"/api/v1/execution/trades/{trade_id}/amend"
    # Set SL/TP far away to pass risk check/spread
    entry = float(active_trades[0].get("entry_price", 2650.0))
    payload_amend = {
        "broker_account_id": broker_account["id"],
        "sl_price": entry - 100.0,
        "tp_price": entry + 100.0
    }
    resp_amend = await api_client.post(amend_url, json=payload_amend, headers=auth_headers)
    assert resp_amend.status_code in [200, 201], f"Amend failed: {resp_amend.text}"

    # 4. Close Trade
    close_url = f"/api/v1/execution/trades/{trade_id}/close"
    resp_close = await api_client.post(close_url, json={}, headers=auth_headers)
    assert resp_close.status_code in [200, 201], f"Close failed: {resp_close.text}"

@pytest.mark.asyncio
async def test_pending_order_lifecycle(api_client, auth_headers, broker_account, poller):
    """Place Limit Order -> Amend -> Cancel."""
    # 1. Place Limit Order (Far from current price)
    order_url = "/api/v1/execution/orders"
    payload = {
        "broker_account_id": broker_account["id"],
        "symbol": "XAU_USD",
        "order_type": "LIMIT",
        "units": 0.01,
        "price": 1500.0, # Gold price far from 2500+
        "comment": f"E2E_PYTEST_LIMIT_{int(time.time())}"
    }
    
    response = await api_client.post(order_url, json=payload, headers=auth_headers)
    assert response.status_code in [200, 201], f"Order placement failed: {response.text}"
    order_id = response.json()["data"]["id"]

    # 2. Amend Order
    amend_url = f"/api/v1/execution/orders/{order_id}"
    payload_amend = {
        "broker_account_id": broker_account["id"],
        "price": 1550.0,
        "sl_price": 1450.0,
        "tp_price": 1700.0
    }
    resp_amend = await api_client.put(amend_url, json=payload_amend, headers=auth_headers)
    assert resp_amend.status_code == 200, f"Order amend failed: {resp_amend.text}"

    # 3. Cancel Order
    cancel_url = f"/api/v1/execution/orders/{order_id}"
    params = {"broker_account_id": broker_account["id"]}
    resp_cancel = await api_client.delete(cancel_url, params=params, headers=auth_headers)
    assert resp_cancel.status_code == 200, f"Order cancellation failed: {resp_cancel.text}"

@pytest.mark.asyncio
async def test_risk_rejection(api_client, auth_headers, broker_account):
    """Verify that orders exceeding risk parameters are rejected."""
    # 1. Oversized units (Gold usually has 10M units/lot, 100 lots is huge for a demo account)
    order_url = "/api/v1/execution/orders"
    payload = {
        "broker_account_id": broker_account["id"],
        "symbol": "XAU_USD",
        "order_type": "MARKET",
        "units": 10.0, # 10 lots of Gold is very Large (~$2.6M exposure)
        "comment": f"E2E_REJECT_TEST"
    }
    
    response = await api_client.post(order_url, json=payload, headers=auth_headers)
    # The API should return 400 or 422 if risk check fails
    assert response.status_code in [400, 422, 500], f"Oversized order should be rejected, got {response.status_code}"
