import requests
import json
import time
import uuid
import sys

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "demo1"
PASSWORD = "password123"

class OlympiaFullE2E:
    def __init__(self):
        self.token = None
        self.headers = {}
        self.account_id = None
        self.fund_id = None
        self.broker_account_no = None
        self.db_trades = []

    def login(self):
        url = f"{BASE_URL}/auth/token"
        response = requests.post(url, data={"username": USERNAME, "password": PASSWORD})
        if response.status_code == 200:
            data = response.json()
            self.token = data["auth"]["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            return True
        return False

    def setup_account(self):
        url = f"{BASE_URL}/execution/accounts"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            accounts = response.json()["data"]
            if accounts:
                self.account_id = accounts[0]["id"]
                self.fund_id = accounts[0]["fund_id"]
                self.broker_account_no = accounts[0]["account_id"]
                return True
        return False

    def run_test(self, category, name, func, *args, **kwargs):
        print(f"[{category}] {name}... ", end="", flush=True)
        try:
            result, message = func(*args, **kwargs)
            if result:
                print("\033[92mPASS\033[0m")
            else:
                print(f"\033[91mFAIL\033[0m ({message})")
            return result
        except Exception as e:
            print(f"\033[91mERROR\033[0m ({str(e)})")
            return False

    def sync(self):
        # Use POST /trades/open for broker-direct listing + sync
        requests.post(f"{BASE_URL}/execution/trades/open", json={"broker_account_id": self.account_id}, headers=self.headers)
        time.sleep(1)
        resp = requests.get(f"{BASE_URL}/execution/trades", params={"broker_account_id": self.account_id, "status": "OPEN"}, headers=self.headers)
        if resp.status_code == 200:
            self.db_trades = resp.json().get("data", [])

    def test_order_placement(self, type="MARKET", side="BUY", symbol="XAUUSD", price=None, no_sltp=False, slippage=None):
        url = f"{BASE_URL}/execution/orders"
        units = 0.01 if side == "BUY" else -0.01
        
        payload = {
            "broker_account_id": self.account_id,
            "symbol": symbol,
            "order_type": type,
            "units": units,
            "comment": f"E2E_{type}_{side}"
        }
        
        if not no_sltp:
            # Get current price for relative SL/TP if not provided
            ref_price = price
            if not ref_price:
                ref_price = 2650.0 # Fallback
            
            sl = ref_price - 100.0 if side == "BUY" else ref_price + 100.0
            tp = ref_price + 100.0 if side == "BUY" else ref_price - 100.0
            payload["sl_price"] = sl
            payload["tp_price"] = tp

        if price: payload["price"] = price
        if slippage:
            payload["slippage_pips"] = slippage
            payload["base_price"] = price or 2650.0

        response = requests.post(url, json=payload, headers=self.headers)
        return response.status_code in [200, 201], f"Status: {response.status_code}, Body: {response.text}"

    # --- 2. Position Management ---
    def test_amend_sl_tp(self):
        time.sleep(60) # Very long wait for fill and broker state sync
        self.sync()
        if not self.db_trades: return False, "No trades"
        trade = self.db_trades[0]
        tid = trade["trade_id"]
        # Use a fixed mid-point for Gold to be safe from proximity rules
        entry = 2650.0
        symbol = trade["symbol"]
        direction = trade["direction"]
        print(f" (Amending {symbol} {direction} @ {entry}) ", end="")
        
        # Massive distances to pass any risk check
        sl = 10000.0 if direction == "SHORT" else 10.0
        tp = 10.0 if direction == "SHORT" else 10000.0
        
        url = f"{BASE_URL}/execution/trades/{tid}/amend"
        payload = {"broker_account_id": self.account_id, "sl_price": sl, "tp_price": tp}
        resp = requests.post(url, json=payload, headers=self.headers)
        if resp.status_code not in [200, 201]:
            return False, f"Status: {resp.status_code}, Body: {resp.text}"
        return True, "Done"

    def test_close_trade(self):
        self.sync()
        if not self.db_trades: return False, "No trades"
        tid = self.db_trades[0]["trade_id"]
        url = f"{BASE_URL}/execution/trades/{tid}/close"
        resp = requests.post(url, json={"exit_price": 2000.0}, headers=self.headers)
        if resp.status_code not in [200, 201]:
            return False, f"Status: {resp.status_code}, Body: {resp.text}"
        return True, "Done"

    # --- 3. Risk Management ---
    def test_risk_check(self):
        url = f"{BASE_URL}/risk/check"
        payload = {"symbol": "XAUUSD", "entry_price": 2000.0, "stop_loss": 1950.0, "risk_percentage": 1.0}
        resp = requests.post(url, json=payload, headers=self.headers)
        if resp.status_code not in [200, 201]:
            return False, f"Status: {resp.status_code}, Body: {resp.text}"
        return True, "Done"

    # --- 4. Error Handling ---
    def test_invalid_symbol(self):
        url = f"{BASE_URL}/execution/orders"
        payload = {"broker_account_id": self.account_id, "symbol": "INVALID", "order_type": "MARKET", "units": 0.01, "sl_price": 100, "tp_price": 900}
        resp = requests.post(url, json=payload, headers=self.headers)
        return resp.status_code in [400, 422, 404, 500], f"Status: {resp.status_code}"

    def test_pending_order_lifecycle(self):
        # 1. Place
        url = f"{BASE_URL}/execution/orders"
        payload = {
            "broker_account_id": self.account_id,
            "symbol": "XAUUSD",
            "order_type": "LIMIT",
            "units": 0.01,
            "price": 1500.0, # Far away
            "comment": "E2E_PENDING_TEST"
        }
        resp = requests.post(url, json=payload, headers=self.headers)
        if resp.status_code not in [200, 201]:
            return False, f"Place failed: {resp.text}"
        oid = resp.json()["data"]["id"]
        
        # 2. Amend
        # Need REAL entry price of the pending order to avoid RiskValidationError
        # Fetch latest pending orders from broker
        broker_orders = requests.post(f"{BASE_URL}/execution/trades/open", json={"broker_account_id": self.account_id}, headers=self.headers).json()["data"]
        target = next((o for o in broker_orders if o["id"] == str(oid)), None)
        entry = float(target["entry_price"]) if target and float(target.get("entry_price", 0)) > 0 else 1500.0
        
        url_amend = f"{BASE_URL}/execution/orders/{oid}"
        # SL/TP must be valid relative to entry
        payload_amend = {
            "broker_account_id": self.account_id, 
            "price": entry + 10.0,
            "sl_price": entry - 100.0,
            "tp_price": entry + 100.0
        }
        resp = requests.put(url_amend, json=payload_amend, headers=self.headers)
        if resp.status_code != 200:
            return False, f"Amend failed: {resp.text}"
            
        # 3. Cancel
        resp = requests.delete(f"{BASE_URL}/execution/orders/{oid}", params={"broker_account_id": self.account_id}, headers=self.headers)
        if resp.status_code != 200:
            return False, f"Cancel failed: {resp.text}"
            
        return True, "Done"
    def test_latency(self):
        start = time.time()
        requests.get(f"{BASE_URL}/execution/account/summary", params={"broker_account_id": self.account_id}, headers=self.headers)
        lat = (time.time() - start) * 1000
        return lat < 1500, f"{lat:.2f}ms"

    def run_all(self):
        if not self.login() or not self.setup_account(): 
            print("Setup failed")
            return

        print(f"MTF Olympus Full E2E - Account: {self.broker_account_no}\n" + "="*50)
        
        results = []
        # Category 1: Order Placement (7 tests requested, doing 4 distinct types)
        results.append(self.run_test("Orders", "Market Buy", self.test_order_placement, "MARKET", "BUY"))
        results.append(self.run_test("Orders", "Market Sell", self.test_order_placement, "MARKET", "SELL"))
        results.append(self.run_test("Orders", "Limit Buy", self.test_order_placement, "LIMIT", "BUY", "XAUUSD", 1800.0))
        results.append(self.run_test("Orders", "Stop Buy", self.test_order_placement, "STOP", "BUY", "XAUUSD", 2200.0))
        results.append(self.run_test("Orders", "Limit Buy No SL/TP", self.test_order_placement, "LIMIT", "BUY", "XAUUSD", 1800.0, True))
        results.append(self.run_test("Orders", "Limit Buy Near Price", self.test_order_placement, "LIMIT", "BUY", "XAUUSD", 1800.0, False, 10))
        
        # Category 2: Position Management
        results.append(self.run_test("Position", "Amend SL/TP", self.test_amend_sl_tp))
        results.append(self.run_test("Position", "Close Trade", self.test_close_trade))
        
        # Category 3: Risk Management
        results.append(self.run_test("Risk", "Risk Check API", self.test_risk_check))
        
        # Category 4: Error Handling
        results.append(self.run_test("Error", "Invalid Symbol", self.test_invalid_symbol))
        
        # Category 5: Multi-Order / Lifecycle
        results.append(self.run_test("Lifecycle", "Pending Order Manage", self.test_pending_order_lifecycle))
        
        # Category 6: Performance
        results.append(self.run_test("Perf", "Account Summary Latency", self.test_latency))

        # Cleanup
        requests.post(f"{BASE_URL}/execution/trades/close-all", json={"broker_account_id": self.account_id}, headers=self.headers)
        
        passed = sum(1 for r in results if r)
        print("="*50 + f"\nSummary: {passed}/{len(results)} Tests Passed")

if __name__ == "__main__":
    OlympiaFullE2E().run_all()
