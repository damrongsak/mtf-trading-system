# cTrader Development Guide

This guide defines mandatory standards and patterns for interacting with the cTrader Open API Protobuf messages in MTF Olympus. AI agents and developers MUST follow these rules to prevent "proto mismatches" and runtime errors.

## 1. Protobuf Field Access Guardrails

### Rule: No Direct `grossProfit` Access on Position
The `ProtoOAPosition` message in the current version of the cTrader library (0.9.2) **does not** contain a `grossProfit` field. This field is only available in specific PnL response messages or calculated via tick events.

**❌ BAD (Causes AttributeError):**
```python
pnl = position.grossProfit / 100.0
```

**✅ GOOD (Defensive):**
```python
pnl = getattr(position, 'grossProfit', 0.0) / 100.0
```

### Rule: Always Use `getattr` for Financial Fields
Due to variations in Protobuf definitions across different cTrader Open API versions, always use `getattr` with a default of `0.0` for the following fields on position/order objects:
- `grossProfit`
- `swap`
- `commission`
- `usedMargin`

## 2. Unit Conversions

### Rule: Monetary Values are in Cents
cTrader expresses monetary values (balance, pnl, swap, commission) as integers representing "cents" (or the smallest currency unit). Always divide by `100.0` for USD-based accounts.

```python
normalized_pnl = raw_pnl / 100.0
```

### Rule: Volume is in "Cents" of the Lot Size
Volume in cTrader is often expressed as an integer. Use the `lot_size` from symbol metadata to convert to universal units.

## 3. Connection Management

### Rule: Use `CTraderConnectionManager`
Do NOT instantiate `CTraderClient` directly. Always use `CTraderConnectionManager.get_client()` to ensure connection pooling and lifecycle management.

## 4. Automated Verification
Run `python scripts/verify_ctrader_standards.py` before committing any changes to cTrader adapters.
