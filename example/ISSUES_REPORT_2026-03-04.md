# Bug Report: MTF Olympus Issues (2026-03-04)

## Issue 1: cTrader Cancel Order Fails

**Title:** Bug: cTrader cancel_order fails with Unexpected response type: 2132

**Description:**
Order cancellation via API fails with error: `Unexpected response type: 2132`

**Steps to Reproduce:**
1. Place an order (e.g., LIMIT order)
2. Attempt to cancel via DELETE `/api/v1/execution/orders/{order_id}`
3. Error: `Unexpected response type: 2132`

**Root Cause:**
File: `services/execution/app/adapters/ctrader_client.py`
- The `cancel_order` method expects `ProtoOAExecutionEvent` payload type
- Received unexpected payload type (2132)
- No error handling for this case

**Fix Required:**
1. Add handling for unexpected payload types in `cancel_order` method
2. Handle `ProtoOAOrderCancelReject` response type
3. Add proper error messages for cancellation failures

---

## Issue 2: Order Direction Wrong (Negative Units)

**Title:** Bug: Negative units converted to positive (BUY instead of SELL)

**Description:**
When placing an order with negative units (e.g., -1000 for SELL), the order is placed as positive units (BUY).

**Steps to Reproduce:**
1. Send order request with `"units": -1000`
2. Order placed as `"units": 1000` (BUY) instead of SELL

**Expected:** SELL order (short)
**Actual:** BUY order (long)

**Root Cause:**
Likely in `services/execution/app/adapters/oanda_order.py` or order validation logic

**Fix Required:**
1. Check unit sign handling in order placement
2. Ensure negative units = SELL, positive = BUY

---

## Issue 3: API Gateway Connection Reset

**Title:** API Gateway returns connection reset

**Description:**
API Gateway intermittently returns "Connection reset by peer" on requests.

**Root Cause:**
Unknown - may need investigation

---
