import requests
import time
import json
import logging
from typing import Dict, Any, List

# --- Configuration ---
API_BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "demo1"
PASSWORD = "password123"
SYMBOL = "XAU_USD"
BASE_RISK_PERCENT = 0.01  # 1% risk per trade
NAV_STOP_OUT = -500.0  # Stop all if floating PnL < -$500
LOT_SIZE_UNIT = 1000  # 0.01 lot = 1000 units (Standardized)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdaptiveTraderBot:
    def __init__(self):
        self.token = None
        self.headers = {}
        self.account_id = None
        self.current_risk = BASE_RISK_PERCENT
        self.ob_tolerance = 0.008 # Default from bb_stoch_ob_v1
        self.active_trades = [] # List of trade IDs to manage

    def login(self):
        url = f"{API_BASE_URL}/auth/token"
        resp = requests.post(url, data={"username": USERNAME, "password": PASSWORD})
        self.token = resp.json()["auth"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def select_account(self):
        url = f"{API_BASE_URL}/execution/accounts"
        resp = requests.get(url, headers=self.headers)
        self.account_id = resp.json()["data"][0]["id"]

    # --- Section 1: Portfolio Monitor & Stop Out ---
    def monitor_portfolio(self):
        url = f"{API_BASE_URL}/execution/account/summary?account_id={self.account_id}"
        resp = requests.get(url, headers=self.headers)
        summary = resp.json()["data"]
        pnl = summary.get("floating_pnl", 0.0)
        
        logger.info(f"NAV: ${summary['nav']:.2f} | PnL: ${pnl:.2f} | Risk Level: {self.current_risk*100}%")

        if pnl <= NAV_STOP_OUT:
            logger.error("STOP OUT HIT! Closing all positions.")
            requests.post(f"{API_BASE_URL}/execution/trades/close-all", 
                          json={"broker_account_id": self.account_id}, headers=self.headers)
        
        # Adaptive Logic: Tighten risk if equity drops
        if pnl < -100:
            self.current_risk = BASE_RISK_PERCENT * 0.5
        else:
            self.current_risk = BASE_RISK_PERCENT

    # --- Section 2: Pro Position Management (BE & Trailing) ---
    def manage_positions(self):
        """Monitor active trades for Break-Even and Trailing Stop logic"""
        # Get open trades from API
        url = f"{API_BASE_URL}/execution/trades/open?broker_account_id={self.account_id}"
        resp = requests.get(url, headers=self.headers)
        open_trades = resp.json()["data"]

        for trade in open_trades:
            trade_id = trade["trade_id"]
            entry = trade["entry_price"]
            current = trade.get("current_price", entry)
            side = trade["side"] # BUY or SELL
            sl = trade.get("sl_price")
            tp = trade.get("tp_price")

            # A. Break-Even Check (if 1:1 RR hit)
            risk_dist = abs(entry - sl) if sl else 0
            if risk_dist > 0:
                if side == "BUY" and (current - entry) >= risk_dist and sl < entry:
                    logger.info(f"Trade {trade_id}: Moving to Break-Even.")
                    self.amend_trade(trade_id, entry)
                elif side == "SELL" and (entry - current) >= risk_dist and sl > entry:
                    logger.info(f"Trade {trade_id}: Moving to Break-Even.")
                    self.amend_trade(trade_id, entry)

    def amend_trade(self, trade_id, new_sl):
        url = f"{API_BASE_URL}/execution/trades/{trade_id}/amend"
        requests.post(url, json={"sl_price": new_sl, "broker_account_id": self.account_id}, headers=self.headers)

    # --- Section 3: Adaptive/RL Logic (System Adaptive) ---
    def sync_market_regime(self):
        """Step 4: AI Suggestion & Super-Strategy Concept"""
        # In a real bot, we would call /analysis/calculate/smc, /analytics/volatility, etc.
        # Here we ask the AI for a consolidated view.
        url = f"{API_BASE_URL}/ai/think"
        payload = {
            "message": f"Analyze {SYMBOL} using BB, Stochastic, and Order Blocks. Is there a 3-bullet entry opportunity?"
        }
        resp = requests.post(url, json=payload, headers=self.headers)
        advice = resp.json()["data"]["response"].lower()
        
        if "trending" in advice:
            self.ob_tolerance = 0.012 # Loosen for trend
            logger.info("AI: Market trending. Loosening OB tolerance.")
        else:
            self.ob_tolerance = 0.005 # Tighten for mean-reversion
            logger.info("AI: Market range-bound. Tightening OB tolerance.")

    # --- Execution ---
    def place_3_bullet_trade(self, side, entry, sl):
        diff = abs(entry - sl)
        targets = [entry + diff, entry + diff*2, entry + diff*3] if side == "BUY" else [entry - diff, entry-diff*2, entry-diff*3]
        
        for i, tp in enumerate(targets):
            payload = {
                "broker_account_id": self.account_id,
                "symbol": SYMBOL,
                "units": LOT_SIZE_UNIT,
                "order_type": "MARKET",
                "sl_price": sl,
                "tp_price": tp,
                "comment": f"Bullet {i+1} [ProBot]"
            }
            requests.post(f"{API_BASE_URL}/execution/orders", json=payload, headers=self.headers)

    def run(self):
        self.login()
        self.select_account()
        while True:
            try:
                self.monitor_portfolio()
                self.manage_positions()
                if int(time.time()) % 3600 < 60: # Every Hour
                    self.sync_market_regime()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = AdaptiveTraderBot()
    bot.run()
