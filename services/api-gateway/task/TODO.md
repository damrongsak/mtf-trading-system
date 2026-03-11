# MTF Olympus - API Gateway & AI Analyst TODO

## API Gateway Test Suite Recovery 🟡
- [x] Fix `test_ai_integration.py` (AI Integration)
- [x] Fix `test_ai_proxy.py` (AI Proxy Response Structure)
- [x] Fix `test_internal_client.py` (Internal Client Mocking)
- [ ] Resolve Regressions in `broker_accounts`, `risk`, and `deployments` (Phase 48 Recovery)
- [ ] Achieve > 60% Code Coverage in API Gateway

## AI Analyst Scaling
- [ ] AI Analyst Scaling: ต่อยอดระบบ Supervisor ให้รองรับ Market Regimes ที่ซับซ้อนขึ้น

## Performance & Stress Testing
- [ ] Execution Latency Benchmarking: วัดผล Latency ของ Decoupled Execution Hot Path (Order -> Fill)
- [ ] Stress Testing (Phase 48): ทดสอบขีดจำกัดของระบบภายใต้คำสั่งซื้อปริมาณมาก (Simulated Market Load)
