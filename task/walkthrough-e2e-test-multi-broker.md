# Walkthrough: Trailing Stop & Janitor Service Fixes

I have successfully debugged and resolved the Trailing Stop verification issues for cTrader and generalized the Janitor Service to support multiple brokers and users.

## Phase 15: cTrader ID Stabilization & Duplicate Fixes
I have resolved the issue where cTrader was creating duplicate trade records and failing amendments due to mismatched `orderId` and `positionId` lifecycles.

### Key Changes
- **[ctrader.py](file:///home/dan/workspace/mtf-trading-system/services/execution/app/adapters/ctrader.py)**:
    - Modified [place_market_order](file:///home/dan/workspace/mtf-trading-system/services/execution/app/adapters/oanda_order.py#40-115) to skip `ORDER_ACCEPTED` events and only publish on true fills (`ORDER_FILLED`, `ORDER_PARTIAL_FILL`).
    - Prioritized `positionId` as the primary identifier for filled trades, ensuring stability for subsequent amendments.
    - Extracted and published `dealId` as a secondary stable identifier.
    - Updated [get_open_trades](file:///home/dan/workspace/mtf-trading-system/services/execution/app/adapters/ctrader.py#319-387) to include **Pending Orders** in the reconciliation list, preventing the Janitor from erroneously closing limit/stop orders.
- **[worker.py](file:///home/dan/workspace/mtf-trading-system/services/execution/app/worker.py)**:
    - Enhanced [FillTradeConsumer](file:///home/dan/workspace/mtf-trading-system/services/execution/app/worker.py#124-299) to store `deal_id` and `broker_position_id` in the `metadata_json`, enabling robust deduplication.
- **[janitor_service.py](file:///home/dan/workspace/mtf-trading-system/services/execution/app/services/janitor_service.py)**:
    - Leverages the updated [get_open_trades](file:///home/dan/workspace/mtf-trading-system/services/execution/app/adapters/ctrader.py#319-387) to correctly distinguish between active orders (now included) and "stray" records (pruned automatically).

### Verification Results
I created a dedicated test suite [test_ctrader_id_stabilization.py](file:///home/dan/workspace/mtf-trading-system/services/execution/tests/test_ctrader_id_stabilization.py) which verifies:
- [x] Event filtering (Skipping `ORDER_ACCEPTED`).
- [x] ID Prioritization (`positionId` over `orderId`).
- [x] Full Reconciliation (Positions + Pending Orders).
- [x] Stable `deal_id` transmission.

### Documentation & Specification Alignment
I have ensured that these changes are fully documented across the system:
- **[specs/03_data_model.yaml](file:///home/dan/workspace/mtf-trading-system/specs/03_data_model.yaml)**: Added `broker_deal_id` to [Trade](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/app/models/trade.py#28-121) and clarified `broker_trade_id` mapping.
- **[specs/04_api_spec.yaml](file:///home/dan/workspace/mtf-trading-system/specs/04_api_spec.yaml)**: Exposed `broker_deal_id` and `broker_trade_id` in [TradeResponse](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/app/schemas/trade.py#83-105).
- **[docs/AI_AGENT_GUIDE.md](file:///home/dan/workspace/mtf-trading-system/docs/AI_AGENT_GUIDE.md)**: Added a "Broker ID Lifecycle" section to guide AI agents on cTrader-specific ID handling.
- **Service READMEs**: Updated [execution](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/app/services/internal_client.py#82-93) and `api-gateway` READMEs with Phase 15 completion details.
- **Models & Schemas**: Synchronized `broker_deal_id` across [execution](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/app/services/internal_client.py#82-93), `api-gateway` models, and Pydantic schemas.

## Changes Made

### 1. Trailing Stop Standardization & Fixes
- **Unified Names**: Standardized the Trailing Stop field name to [trailing_stop](file:///home/dan/workspace/mtf-trading-system/services/execution/scripts/test_e2e_ctrader.py#262-302) across all services, while maintaining `trailing_sl` as an alias for backward compatibility.
- **Adapter Fix**: Corrected a variable scoping error (`s_name`) in the [ctrader.py](file:///home/dan/workspace/mtf-trading-system/services/execution/app/adapters/ctrader.py) adapter's [get_open_trades](file:///home/dan/workspace/mtf-trading-system/services/execution/app/adapters/ctrader.py#319-387) method.
- **DB Sync Fix**: Updated the execution service's [amend_position](file:///home/dan/workspace/mtf-trading-system/services/execution/app/adapters/ctrader.py#658-720) and [amend_order](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/app/routers/execution.py#573-602) endpoints to use both `broker_trade_id` and `broker_account_id` when syncing to the local database, preventing duplication errors.
- **Model Updates**: Updated Pydantic models in the [execution](file:///home/dan/workspace/mtf-trading-system/services/api-gateway/app/services/internal_client.py#82-93) service to support both [trailing_stop](file:///home/dan/workspace/mtf-trading-system/services/execution/scripts/test_e2e_ctrader.py#262-302) and `trailing_sl` aliases.

### 2. Janitor Service Generalization
- **Multi-Broker Support**: Re-implemented the [JanitorService](file:///home/dan/workspace/mtf-trading-system/services/execution/app/services/janitor_service.py#14-116) to be broker-agnostic. It now iterates through active users and their preferences to reconcile accounts for both OANDA and cTrader.
- **Preference Flags**: Added `ctrader_janitor_enabled` and `oanda_janitor_enabled` to [UserPreferences](file:///home/dan/workspace/mtf-trading-system/services/execution/app/models.py#204-212) and implemented the corresponding DTO updates in the `api-gateway`.

### 3. Symbol Resolution & Cache
- **Envelope Handling**: Fixed an issue where the [ExecutionCache](file:///home/dan/workspace/mtf-trading-system/services/execution/app/services/cache_service.py#11-205) was failing to unwrap the [APIResponse](file:///home/dan/workspace/mtf-trading-system/services/execution/app/schemas/response.py#86-96) envelope when fetching symbols from the `api-gateway`, causing symbol resolution failures.
- **Normalizing Names**: Improved symbol name normalization in [ctrader.py](file:///home/dan/workspace/mtf-trading-system/services/execution/app/adapters/ctrader.py) to handle both `EURUSD` and `EUR/USD` formats.

## Verification Results

### Automated E2E Tests
The [test_e2e_ctrader.py](file:///home/dan/workspace/mtf-trading-system/services/execution/scripts/test_e2e_ctrader.py) suite was run and achieved a **100% pass rate**, including the critical Trailing Stop verification phase.

> [!NOTE]
> All phases from Authentication to Limit/Market Orders and Trailing Stop passed successfully.

```bash
Starting Olympus Gateway cTrader E2E Tester...
✅ [Auth] Successfully acquired JWT token.
✅ [Account] Found CTRADER Account ID: bb641c25-2f02-4b45-8f9e-d5b21cb8c155
✅ [Init Prefs] Janitor enabled for OANDA/CTRADER
...
✅ [Enable Trailing Stop] Successfully ENABLED Trailing Stop Loss
✅ [Verify Trailing SL] Confirmed status is True in live state.
✅ [Cancel Order] Order 58276357 cancelled.
🎉 Olympus E2E Integration Suite Completed for cTrader!
```

### Janitor Service Logs
Verified that the Janitor Service is correctly reconciling multiple accounts and detecting desyncs for cTrader:

```text
INFO:app.services.janitor_service:🧹 [Janitor] Starting multi-account reconciliation...
INFO:app.services.janitor_service:🧹 [Janitor] Reconciling OANDA account Trader2 OANDA (001-011-437083-005)
INFO:app.services.janitor_service:🧹 [Janitor] Account Trader2 OANDA is perfectly in sync.
INFO:app.services.janitor_service:🧹 [Janitor] Reconciling CTRADER account Trader1 cTrader Live (40816494)
INFO:app.services.janitor_service:🧹 [Janitor] Processed 32 desyncs for Trader1 cTrader Live.
INFO:app.services.janitor_service:🧹 [Janitor] Reconciliation cycle complete. Synced 2 accounts.
```

### Visual Verification
- Trailing Stop status of `True` was confirmed via the API response in Phase 10.
- Database synchronization was verified via Phase 5 and Phase 8 (Amendments).
