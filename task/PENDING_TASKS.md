# ⚠️ Pending Tasks - High Volatility Delay (2026-03-09)

The following tasks are deferred due to high market volatility and are not safe for live environment testing at this time.

## 🔴 Deferred: Live Environment Tests
- [ ] **Live E2E Verification (cTrader)**: Run `test_e2e_ctrader.py` to confirm `positionId` propagation to Dashboard in live environment (Phase 15 Action Item).
- [ ] **Trailing Stop Verification**: Test `Trailing Stop Loss` submission to cTrader API via `/trades/amend` endpoint.

## 🟡 Deferred: Performance Optimization
- [ ] **HFT-Lite Optimization**: Refactor `_save_filled_trade_to_db` in `ctrader.py` to use a full **Redis Stream** producer/consumer model for fill persistence.

---
*Note: Resume these tasks only when market conditions stabilize or using a dedicated paper/sandbox environment with isolated risk.*
