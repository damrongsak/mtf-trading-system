# Solo Trader (demo1) Command Center

Welcome to the `demo1_trader` specialized command center. This directory contains production-ready scripts for the **MTF Olympus Solo Trader System**.

## 📂 Directory Contents

| File | Description |
| :--- | :--- |
| `solo_trader_dashboard.py` | Professional adaptive bot with BE, Trailing Stop, and AI alignment. |
| `ws_monitor.py` | Real-time price and spread monitor via WebSockets. |

## 🚀 Getting Started

### 1. Requirements
Ensure you have the required Python libraries installed:
```bash
pip install requests websockets
```

### 2. Configure Credentials
Open the scripts and verify your `API_BASE_URL` and `USERNAME/PASSWORD`. Default is set to:
- **URL:** `http://localhost:8000/api/v1`
- **User:** `demo1` / `password123`

### 3. Run the Price Monitor
Keep this running in a separate terminal to see real-time XAU_USD ticks:
```bash
python scripts/demo1_trader/ws_monitor.py
```

### 4. Launch the Adaptive Bot
This bot manages your portfolio, hits emergency stop-outs, and aligns with AI regimes:
```bash
python scripts/demo1_trader/solo_trader_dashboard.py
```

## 📚 Documentation
For the full tactical guide, multi-order strategy, and "Super-Strategy" logic, refer to the:
- [MTF Solo Trader Manual](../../docs/trader_manual.md)

---
*Powered by MTF Olympus v2.5 AI Orchestrator*
