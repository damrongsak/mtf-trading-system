# MTF Olympus - API Gateway & AI Analyst TODO

## API Gateway Test Suite Recovery 🟡
- [x] Fix `test_ai_integration.py` (AI Integration)
- [x] Fix `test_ai_proxy.py` (AI Proxy Response Structure)
- [x] Fix `test_internal_client.py` (Internal Client Mocking)
- [ ] Resolve Regressions in `broker_accounts`, `risk`, and `deployments` (Phase 48 Recovery)
- [ ] Achieve > 60% Code Coverage in API Gateway

# MTF Olympus - API Gateway### [Component] AI Analyst (`services/ai-analyst`)

#### [MODIFY] [strategy_advisor.py](file:///home/dan/workspace/mtf-trading-system/services/ai-analyst/app/agents/strategy_advisor.py)
- **Enhance `node_severity_classifier`**:
    - Integrate `GetMarketContextTool` to fetch real-time volatility data.
    - Escalation to `CRISIS` based on market regime shift.
- **Update `AgentState`**: Add `market_regime` and `volatility_score`.

#### [MODIFY] [agents.py](file:///home/dan/workspace/mtf-trading-system/services/ai-analyst/app/routers/agents.py)
- **Consolidate Endpoints**:
    - Implement a single `/api/v1/ai/think` endpoint that routes to the appropriate specialist via the `SupervisorAgent`.
    - Deprecate fragmented endpoints (`/agent/observer/run`, `/agent/briefing`, etc.) in favor of the unified orchestrator.
- **Optimization**: Implement global standard response headers and caching for routine briefings.

#### [MODIFY] [supervisor.py](file:///home/dan/workspace/mtf-trading-system/services/ai-analyst/app/agents/supervisor.py)
- Refactor to handle 'intent' as the primary routing signal, incorporating `daily_briefing` and `market_observer` as specialist nodes under one supervisor.

## Performance & Stress Testing
- [ ] Execution Latency Benchmarking: วัดผล Latency ของ Decoupled Execution Hot Path (Order -> Fill)
- [ ] Stress Testing (Phase 48): ทดสอบขีดจำกัดของระบบภายใต้คำสั่งซื้อปริมาณมาก (Simulated Market Load)
