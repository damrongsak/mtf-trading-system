# 🤖 AI Agent Handoff: MTF Olympus - Broker Integration & ID Stabilization

## 📅 Current Status: 2026-03-07
**Phase 15 (cTrader ID Stabilization & Duplicate Fixes)** is **COMPLETED** and documented. The system is now resilient against double-reporting of fills and mismatched identifier lifecycles in cTrader.

---

## ✅ What Has Been Accomplished

### 1. cTrader ID Stabilization (The "Stable ID" Fix)
- **Unified ID Mapping**: Modified `ctrader.py` to prioritize `positionId` over `orderId` for all filled market orders. This ensures `broker_trade_id` in the database always uses the ID required for SL/TP amendments.
- **Event Filtering**: Re-engineered `place_market_order` to skip `ORDER_ACCEPTED` events and only publish fill data on true fills (`ORDER_FILLED`, `ORDER_PARTIAL_FILL`). This prevents duplicate trade records.
- **Deduplication Logic**: Updated `FillTradeConsumer` in `worker.py` to store/use `broker_deal_id` (from `dealId`) as a secondary stable identifier for mapping fills.

### 2. Generalization of "The Janitor" (Reconciliation)
- **Multi-Entitiy Sync**: Updated `get_open_trades` in the cTrader adapter to include **Pending Orders** alongside Open Positions.
- **Pruning Safety**: The Janitor now correctly distinguishes between active limit orders (which should be kept) and "stray" records, preventing accidental trade closures.
- **Cross-Broker Support**: The Janitor is now generalized to handle both OANDA and cTrader accounts across all users.

### 3. Specification & Documentation Alignment (SDD)
- **Spec Updates**: 
    - `specs/03_data_model.yaml`: Added `broker_deal_id` to `Trade` entity.
    - `specs/04_api_spec.yaml`: Exposed `broker_deal_id` in `TradeResponse`.
- **Operational Guide**: Updated `docs/AI_AGENT_GUIDE.md` with a **"Broker ID Lifecycle"** section detailing the `orderId` -> `positionId` transition.
- **Service Docs**: Updated READMEs for `execution` and `api-gateway` with Phase 15 milestones.

---

## 🚧 Current Work / Just Finished
- **Verification**: All core logic verified via `tests/test_ctrader_id_stabilization.py` (Mocked Protobuf responses).
- **Alignment**: Models and Pydantic schemas are synchronized across all backend services.

---

## 🚀 Next Steps (Action Items for Next Agent)

1.  **Live E2E Verification**:
    - Run `docker compose exec execution uv run python scripts/test_e2e_ctrader.py` with a **live micro-account**.
    - **Goal**: Confirm that the `positionId` correctly propagates back to the Dashboard and that subsequent SL/TP amendments do not result in "404 Not Found" errors on the broker.

2.  **Trailing Stop Verification**:
    - Ensure that enabling Trailing Stop via the `/trades/amend` endpoint correctly maps to the `trailingStopLoss` flag in the cTrader Open API payload.
    - Verify visual movement on the cTrader terminal during live price movement.

3.  **HFT-Lite Optimization**:
    - **Task**: Refactor `_save_filled_trade_to_db` in `ctrader.py`.
    - **Current state**: Uses `asyncio.create_task` which is non-blocking but runs on the same event loop.
    - **Optimization**: Move to a full **Redis Stream** producer/consumer model for fill persistence to ensure the WebSocket adapter loop is purely I/O bound.

4.  **Symbol Mapping Resilience**:
    - Investigate edge cases where symbol names (e.g., `EURUSD` vs `EUR_USD`) might cause reconciliation mismatches if the `ExecutionCache` is partially stale.

---

## 📂 Key Files to Reference
- **Adapter Logic**: `services/execution/app/adapters/ctrader.py`
- **Verification Tests**: `services/execution/tests/test_ctrader_id_stabilization.py`
- **Data Model**: `specs/03_data_model.yaml` (Look for `Trade` entity)
- **Agent Guide**: `docs/AI_AGENT_GUIDE.md` (See *Broker ID Lifecycle*)

**Good luck, Agent. The core architecture is stable—focus on live verification and latency optimization.**
