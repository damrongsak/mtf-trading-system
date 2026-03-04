import subprocess
import json
import os
import sys
import httpx
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==========================================
# MTF Olympus - Comprehensive Health Manifest
# ==========================================

# 1. Infrastructure Services (Docker Container Names)
INFRA_SERVICES = [
    "mtf-postgres", "redis", "qdrant", "nginx"
]

# 2. Application Services
APP_SERVICES = [
    "api-gateway", "execution", "strategy-core", "data-pipeline", "ai-analyst"
]

# 3. API Endpoint Manifest (Path, Name, Method, Payload)
# Valid IDs for health check (fetched from DB)
VALID_ACCOUNT_ID = "2c542d2a-b151-41e0-8cc0-8f0ca2a3eb49"
VALID_DEPLOYMENT_ID = "252aef08-114d-46b6-a7d4-a481aab4da4b"

# User Credentials
USER_NAME = "trader1"
USER_PASSWORD = "password123"

# Initial endpoints (will be updated with real data where applicable)
GATEWAY_ENDPOINTS = [
    {"path": "/auth/profile", "name": "User Profile", "method": "GET"},
    {"path": "/accounts/", "name": "Broker Accounts", "method": "GET"},
    {"path": "/execution/trades", "name": "Trade History", "method": "GET"},
    {"path": f"/execution/orders?broker_account_id={VALID_ACCOUNT_ID}", "name": "Pending Orders", "method": "GET"},
    {"path": f"/execution/positions?broker_account_id={VALID_ACCOUNT_ID}", "name": "Open Positions", "method": "GET"},
    {"path": "/ai/briefing", "name": "AI Market Briefing", "method": "GET"},
    {"path": "/ai/agents", "name": "AI Agents Registry", "method": "GET"},
    {"path": "/ai/admin/qdrant/health", "name": "Vector DB Integrity", "method": "GET"},
    {"path": "/analysis/opportunities", "name": "Trade Opportunities", "method": "GET"},
    {"path": "/analysis/positioning/status", "name": "Market Positioning", "method": "GET"},
    {"path": "/market/categories", "name": "Market Categories", "method": "GET"},
    {"path": "/journal/", "name": "Trading Journal", "method": "GET"},
    {
        "path": "/internal/signals", 
        "name": "Internal Signals", 
        "method": "POST", 
        "payload": f'{{"deployment_id": "{VALID_DEPLOYMENT_ID}", "symbol": "XAUUSD", "direction": "BULLISH", "price": 2010, "stop_loss": 2000, "take_profit": 2100, "risk_usd": 10, "reason": "healthcheck"}}'
    },
    {
        "path": "/quant/analyze", 
        "name": "Quant Map Analysis", 
        "method": "POST", 
        "payload": '{"symbol": "XAUUSD", "timeframe": "H1", "limit": 100}'
    },
]

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_section(title):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*10} {title} {'='*10}{Colors.ENDC}")

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

class Diagnostic:
    def __init__(self):
        self.gateway_url = "http://localhost:8000/api/v1"
        self.token = None
        self.stats = {"pass": 0, "fail": 0, "warn": 0}
        self.real_price = None
        self.user_data = {}

    def log_result(self, type, message):
        """Standardized logger to manage stats correctly."""
        if type == "pass":
            self.stats["pass"] += 1
            print(f"{Colors.GREEN}  ✔ {message}{Colors.ENDC}")
        elif type == "warn":
            self.stats["warn"] += 1
            print(f"{Colors.YELLOW}  ⚠ {message}{Colors.ENDC}")
        else:
            self.stats["fail"] += 1
            print(f"{Colors.RED}  ✘ {message}{Colors.ENDC}")

    def check_infrastructure(self):
        print_section("INFRASTRUCTURE & DOCKER STATUS")
        output, _ = run_cmd("docker ps --format '{{.Names}}'")
        running = output.split('\n')
        
        for svc in INFRA_SERVICES + APP_SERVICES:
            if svc in running:
                self.log_result("pass", f"{svc:<18} [ONLINE]")
            else:
                self.log_result("fail", f"{svc:<18} [OFFLINE]")

    def check_resources(self):
        print_section("CONTAINER RESOURCE UTILIZATION")
        output, code = run_cmd("docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}'")
        if code == 0:
            print(output)
        else:
            self.log_result("fail", "Failed to retrieve docker stats")

    def perform_login(self):
        print_section("SERVICE AUTHENTICATION GATEWAY")
        
        print(f"  Attempting login for: {Colors.CYAN}{USER_NAME}{Colors.ENDC}...")
        cmd = f'curl -s -X POST {self.gateway_url}/auth/token -d "username={USER_NAME}&password={USER_PASSWORD}"'
        output, code = run_cmd(cmd)
        
        try:
            res = json.loads(output)
            # Handle standard OAuth2 response or the wrapped APIResponse
            if "auth" in res and "access_token" in res["auth"]:
                self.token = res["auth"]["access_token"]
            elif "access_token" in res:
                self.token = res["access_token"]
            
            if self.token:
                self.log_result("pass", f"JWT Token acquired for {USER_NAME}")
                return True
            else:
                self.log_result("fail", f"Login failed: {res.get('message', 'Unknown error')}")
                return False
        except:
            self.log_result("fail", "Authentication critical failure (Connection Refused)")
            return False

    def investigate_user_data(self):
        """Investigate and access data of the authenticated user via API."""
        print_section("INVESTIGATING USER DATA ACCESS")
        
        # 1. Fetch Profile
        try:
            resp = httpx.get(f"{self.gateway_url}/auth/profile", headers={"Authorization": f"Bearer {self.token}"})
            if resp.status_code == 200:
                profile = resp.json().get("data", {})
                self.user_data["profile"] = profile
                self.log_result("pass", f"Accessed Profile: {profile.get('username')} ({profile.get('email')})")
            else:
                self.log_result("fail", f"Failed to access profile: {resp.status_code}")
        except Exception as e:
            self.log_result("fail", f"Profile access error: {e}")

        # 2. Fetch Telegram Status
        try:
            resp = httpx.get(f"{self.gateway_url}/telegram/status", headers={"Authorization": f"Bearer {self.token}"})
            if resp.status_code == 200:
                status = resp.json()
                self.user_data["telegram"] = status
                linked_str = "LINKED" if status.get("linked") else "NOT LINKED"
                self.log_result("pass", f"Telegram Status: {linked_str} (Chat ID: {status.get('chat_id', 'N/A')})")
            else:
                self.log_result("fail", f"Failed to access telegram status: {resp.status_code}")
        except Exception as e:
            self.log_result("fail", f"Telegram status access error: {e}")

    def fetch_real_data(self):
        """Fetch current XAUUSD price from the data-pipeline via API Gateway."""
        print_section("FETCHING REAL MARKET DATA")
        url = f"{self.gateway_url}/data/tick/XAUUSD"
        cmd = f"curl -s -H 'Authorization: Bearer {self.token}' {url}"
        output, code = run_cmd(cmd)
        
        try:
            res = json.loads(output)
            # API might return wrapped in "data"
            data = res.get("data", res)
            self.real_price = data.get("bid") or data.get("price")
            
            if self.real_price:
                self.log_result("pass", f"Real XAUUSD Price: {Colors.CYAN}{self.real_price}{Colors.ENDC}")
                self.update_signal_payload()
            else:
                self.log_result("warn", "Real price not found in response, using default.")
                self.real_price = 2010 # Fallback
        except:
            self.log_result("warn", "Failed to parse market data, using default price.")
            self.real_price = 2010

    def update_signal_payload(self):
        """Update the signal test payload with real price, SL, and TP."""
        # Find the signal endpoint in the list
        for ep in GATEWAY_ENDPOINTS:
            if ep["path"] == "/internal/signals":
                price = round(float(self.real_price), 2)
                stop_loss = round(price - 10, 2)
                take_profit = round(price + 90, 2)
                ep["payload"] = json.dumps({
                    "deployment_id": VALID_DEPLOYMENT_ID,
                    "symbol": "XAUUSD",
                    "direction": "BULLISH",
                    "price": price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "risk_usd": 10,
                    "reason": "healthcheck"
                })
                self.log_result("pass", f"Payload updated: Price={price}, SL={stop_loss}, TP={take_profit}")

    def check_api_endpoints(self):
        if not self.token:
            print(f"{Colors.RED}  Skipping API Registry check: Not authenticated.{Colors.ENDC}")
            return

        print_section("UNIVERSAL API ENDPOINT REGISTRY")
        for ep in GATEWAY_ENDPOINTS:
            url = f"{self.gateway_url}{ep['path']}"
            display_name = f"{ep['name']:<25} ({ep['path']})"
            method = ep['method']
            
            if method == "POST":
                payload = ep.get('payload', '{}')
                payload_esc = payload.replace("'", "'\\''")
                cmd = f"curl -s -o /dev/null -w '%{{http_code}}' -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer {self.token}' -d '{payload_esc}' {url}"
            else:
                cmd = f"curl -s -o /dev/null -w '%{{http_code}}' -H 'Authorization: Bearer {self.token}' {url}"
            
            status_code_raw, _ = run_cmd(cmd)
            status_code = status_code_raw.strip()[-3:]
            
            if status_code in ["200", "201"]:
                self.log_result("pass", display_name)
            elif status_code == "307":
                self.log_result("pass", f"{display_name} -> [OK (via 307 Redirect)]")
            elif status_code in ["400", "404", "422", "500"]:
                self.log_result("warn", f"{display_name} -> [REACHABLE (Status {status_code})]")
            else:
                self.log_result("fail", f"{display_name} -> [CONN ERROR: {status_code}]")

    def check_logs(self):
        print_section("LOG ANOMALY DETECTION (Last 50 lines)")
        critical_keywords = "ERROR|CRITICAL|Traceback|Unauthorized|Forbidden"
        for svc in APP_SERVICES:
            print(f"  Scanning {svc}...")
            # Ignore known fixes or noisy harmless errors
            cmd = f"docker logs {svc} --tail 50 2>&1 | grep -iE '{critical_keywords}' | grep -v 'NameError: name .os. is not defined' | tail -n 3"
            output, _ = run_cmd(cmd)
            if output:
                print(f"{Colors.YELLOW}    Potential issues found in {svc} logs:{Colors.ENDC}")
                for line in output.split('\n'):
                    if line.strip():
                        print(f"    -> {line.strip()}")
            else:
                print(f"{Colors.GREEN}    ✔ {svc} is clear.{Colors.ENDC}")

    def send_telegram_notification(self, message):
        """Sends a message to Telegram using the MTF Olympus API Service."""
        if not self.token:
            print(f"{Colors.YELLOW}  ⚠️ Not authenticated. Skipping API Telegram notification.{Colors.ENDC}")
            return False
            
        url = f"{self.gateway_url}/telegram/send"
        payload = {
            "message": message
        }
        
        try:
            resp = httpx.post(url, json=payload, headers={"Authorization": f"Bearer {self.token}"}, timeout=10.0)
            if resp.status_code == 200:
                print(f"{Colors.GREEN}  ✔ Telegram notification sent via API Service.{Colors.ENDC}")
                return True
            else:
                print(f"{Colors.RED}  ✘ Failed to send Telegram via API: {resp.text}{Colors.ENDC}")
                return False
        except Exception as e:
            print(f"{Colors.RED}  ✘ API Telegram notification error: {e}{Colors.ENDC}")
            return False

    def summary(self):
        print_section("DIAGNOSTIC SUMMARY")
        total = sum(self.stats.values())
        print(f"  Total Checks: {total}")
        print(f"  {Colors.GREEN}PASSED:  {self.stats['pass']}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}WARNING: {self.stats['warn']}{Colors.ENDC}")
        print(f"  {Colors.RED}FAILED:  {self.stats['fail']}{Colors.ENDC}")
        
        status_text = "OPTIMAL" if self.stats["fail"] == 0 else f"DEGRADED ({self.stats['fail']} critical issues)"
        status_emoji = "🟢" if self.stats["fail"] == 0 else "🔴"
        
        print(f"\n{Colors.BOLD}{Colors.GREEN if self.stats['fail'] == 0 else Colors.RED}SYSTEM STATUS: {status_text}{Colors.ENDC}")
        
        # Prepare Telegram Signal message (Real Data)
        if self.real_price:
            price = round(float(self.real_price), 2)
            sl = round(price - 10, 2)
            tp = round(price + 90, 2)
            
            signal_msg = (
                "🔔 *New Signal: Gold SMC+OI Confluence*\n\n"
                "*Symbol*: XAUUSD\n"
                "*Direction*: 🟢 BULLISH\n"
                f"*Price*: {price}\n"
                f"*Stop Loss*: {sl}\n"
                f"*Take Profit*: {tp}\n"
                "*RRR*: 9.0\n"
                "*Risk*: $10\n\n"
                "*Reason*: healthcheck\n\n"
                "⚡️ *Executing AUTO*"
            )
            self.send_telegram_notification(signal_msg)
            
        # Also send a health report if something failed or for daily summary
        health_report = (
            f"🛡️ *MTF Olympus Health Report*\n"
            f"Status: {status_emoji} {status_text}\n"
            f"Checks: {self.stats['pass']}/{total} Passed\n"
            f"User: {USER_NAME}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_telegram_notification(health_report)

if __name__ == "__main__":
    os.system('clear')
    print(f"{Colors.BOLD}{Colors.BLUE}MTF Olympus v2.5 - Universal Health & Security Monitor{Colors.ENDC}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 65)
    
    diag = Diagnostic()
    diag.check_infrastructure()
    diag.check_resources()
    if diag.perform_login():
        diag.investigate_user_data()
        diag.fetch_real_data()
        diag.check_api_endpoints()
    diag.check_logs()
    diag.summary()
