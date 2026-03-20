# MTF Olympus: Solo Trader Manual (v2.2 - Pro Edition)

Welcome to the **Wealth Operating System**. This manual provides the technical blueprints for a solo trader to dominate the XAU/USD market using the MTF Olympus infrastructure, now with **Pro Position Management** and **Adaptive AI Optimization**.

---

## 1. Authentication (Getting the Key)

To interact with the system, you must first obtain a JWT access token.

### Quick Start (cURL)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/token" \
     -d "username=demo1&password=password123"
```

---

## 2. Portfolio Monitoring & Safety

### Fetch Account Summary
**Endpoint:** `GET /api/v1/execution/account/summary`
```python
headers = {"Authorization": f"Bearer {token}"}
resp = requests.get("http://localhost:8000/api/v1/execution/account/summary", headers=headers)
summary = resp.json()["data"]
print(f"NAV: ${summary['nav']} | Margin Level: {summary['margin_level']}%")
```

### Emergency Stop Out (Logic)
Monitor your drawdown. If `nav < threshold`, trigger an emergency close.
```python
if summary['floating_pnl'] < -500: # Example $500 loss limit
    requests.post("http://localhost:8000/api/v1/execution/trades/close-all", 
                  json={"broker_account_id": "YOUR_ACCOUNT_ID"}, headers=headers)
```

---

## 3. Pro Position Management (Dynamic Exits)

Institutional trading is about managing the trade *after* entry.

### A. Break-Even (BE) Logic
Once Bullet 1 hits its 1:1 Risk-Reward (RR) target, the bot should automatically move the Stop-Loss for Bullets 2 and 3 to the entry price to secure a "Risk-Free" trade.

```python
def move_to_breakeven(trade_id, entry_price):
    payload = {"sl_price": entry_price}
    requests.put(f"http://localhost:8000/api/v1/execution/trades/{trade_id}/amend", 
                 json=payload, headers=headers)
```

### B. ATR Trailing Stop
Use the current Average True Range (ATR) to trail your stop-loss, protecting profits during trending moves.

```python
def apply_trailing_stop(trade_id, current_price, atr, side):
    # Trail 2.5 * ATR away from current price
    if side == "BUY":
        new_sl = current_price - (atr * 2.5)
    else:
        new_sl = current_price + (atr * 2.5)
    
    payload = {"sl_price": new_sl}
    requests.put(f"http://localhost:8000/api/v1/execution/trades/{trade_id}/amend", 
                 json=payload, headers=headers)
```

---

## 4. Multi-Order "3-Bullet" Strategy

Split your risk into 3 "bullets" with tiered targets to maximize capture.

### The Standard Pattern:
- **Bullet 1**: TP at 1:1 RR (Cover costs).
- **Bullet 2**: TP at 1:2 RR (Profit engine).
- **Bullet 3**: TP at 1:3 RR (Runner).

---

## 5. Adaptive AI Optimization (Mini-RL)

To align with the market like an AGI agent, the system uses a "Mini RL" loop that adjusts parameters based on performance.

### Logic:
- **Win Rate Monitoring**: If the last 5 trades have < 40% win rate, tighten the **Order Block** filter tolerance (`ob_tolerance`).
- **Drawdown Scaling**: If PnL is in drawdown, reduce `risk_per_trade` to 0.5%.

### AI Co-Pilot Consultation
Ask the AI to evaluate market regimes:
```python
ai_response = requests.post("http://localhost:8000/api/v1/ai/think", 
                            json={"message": "Is XAU_USD in a trendy or range-bound regime? Adjust my BB filters."}, 
                            headers=headers)
print(f"AI ADVICE: {ai_response.json()['data']['response']}")
```

---

## 6. Real-Time Scripts & Automation

The core of your solo trader journey is the **Adaptive Trading Bot**, located at [scripts/demo1_trader/solo_trader_dashboard.py](../scripts/demo1_trader/solo_trader_dashboard.py).

To monitor prices in real-time, run the [scripts/demo1_trader/ws_monitor.py](../scripts/demo1_trader/ws_monitor.py):
```bash
# Monitor price fluctuations without polling the REST API.
python scripts/demo1_trader/ws_monitor.py
```

---
**Institutional Standard** | *Build Wealth, Not Just Bots.*
