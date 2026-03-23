# Institutional Roadmap: Phase 40-70 (Session 2026-03-24)

This document tracks the progress of advanced institutional features for MTF Olympus.

## ✅ Phase 40: AI Correlation-Aware Risk Scaling (Completed)
Dynamic, PCA-based correlation risk engine that prevents factor-concentration.
- [x] **PCA Engine**: Exposes `POST /api/v1/ai/risk/correlation` in `ai-analyst`.
- [x] **CorrelationService**: Daily background loop in `execution` for price fetching and PCA updates.
- [x] **Active Symbol Tracking**: Real-time Redis SET (`fund:{id}:active_symbols`) for overlap detection.
- [x] **Kc Multiplier ($K_c$)**: 0.70x protective cut applied in `RiskParityEngine` during systemic alerts.
- [x] **Institutional UI**: Enhanced `RiskParityTable.tsx` with PC1 loadings and systemic hazard alerts.

## 🚀 Future Roadmap

### Phase 50: Advanced Portfolio Optimization (Black-Litterman) <!-- id: 50 -->
- [ ] Integrate Black-Litterman model with AI Analyst "Views".
- [ ] Implement Bayesian weight adjustment logic.
- [ ] Update Portfolio Dashboard for 2nd order optimization.

### Phase 60: Institutional Compliance & Reporting (Audit Trail) <!-- id: 60 -->
- [ ] Implement trade execution immutable logs (Audit Trail).
- [ ] Generate daily institutional performance reports (PDF/JSON).
- [ ] Create audit trail UI for factor-level analysis.

### Phase 70: AI-Agentic Self-Correction (Self-Healing Strategies) <!-- id: 70 -->
- [ ] Implement strategy-drift feedback loop (RLHF/Loopback).
- [ ] Automated parameter tuning nodes in AI Analyst.
- [ ] Self-healing execution guardrails for unexpected volatility.

---
*Last Updated: 2026-03-24 by AI Analyst*
