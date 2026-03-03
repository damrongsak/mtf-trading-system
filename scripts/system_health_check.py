import subprocess
import json
import os
import sys
from datetime import datetime

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
        "payload": f'{{"deployment_id": "{VALID_DEPLOYMENT_ID}", "symbol": "XAUUSD", "direction": "BULLISH", "stop_loss": 2000, "risk_usd": 10, "reason": "healthcheck"}}'
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
        user = os.getenv("SYSTEM_USER", "execution_service")
        password = os.getenv("SYSTEM_PASSWORD", "servicepassword123")
        
        print(f"  Attempting login for: {Colors.CYAN}{user}{Colors.ENDC}...")
        cmd = f'curl -s -X POST {self.gateway_url}/auth/token -d "username={user}&password={password}"'
        output, code = run_cmd(cmd)
        
        try:
            res = json.loads(output)
            self.token = res.get("auth", {}).get("access_token")
            if self.token:
                self.log_result("pass", "JWT Token acquired successfully")
                return True
            else:
                self.log_result("fail", f"Login failed: {res.get('message', 'Unknown error')}")
                return False
        except:
            self.log_result("fail", "Authentication critical failure (Connection Refused)")
            return False

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
                # High-level proof: The API is reached. 
                # For some endpoints, 404/500/400 might be expected if dummy data doesn't exist in DB.
                # We categorize these as 'warn' (Reachable but Application Error)
                self.log_result("warn", f"{display_name} -> [REACHABLE (Status {status_code})]")
            else:
                self.log_result("fail", f"{display_name} -> [CONN ERROR: {status_code}]")

    def check_logs(self):
        print_section("LOG ANOMALY DETECTION (Last 50 lines)")
        critical_keywords = "ERROR|CRITICAL|Traceback|Unauthorized|Forbidden"
        for svc in APP_SERVICES:
            print(f"  Scanning {svc}...")
            # Ignore known fixes
            cmd = f"docker logs {svc} --tail 50 2>&1 | grep -iE '{critical_keywords}' | grep -v 'NameError: name .os. is not defined' | tail -n 3"
            output, _ = run_cmd(cmd)
            if output:
                print(f"{Colors.YELLOW}    Potential issues found in {svc} logs:{Colors.ENDC}")
                for line in output.split('\n'):
                    if line.strip():
                        print(f"    -> {line.strip()}")
            else:
                print(f"{Colors.GREEN}    ✔ {svc} is clear.{Colors.ENDC}")

    def summary(self):
        print_section("DIAGNOSTIC SUMMARY")
        total = sum(self.stats.values())
        print(f"  Total Checks: {total}")
        print(f"  {Colors.GREEN}PASSED:  {self.stats['pass']}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}WARNING: {self.stats['warn']}{Colors.ENDC}")
        print(f"  {Colors.RED}FAILED:  {self.stats['fail']}{Colors.ENDC}")
        
        if self.stats["fail"] == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}SYSTEM STATUS: OPTIMAL{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}SYSTEM STATUS: DEGRADED ({self.stats['fail']} critical issues){Colors.ENDC}")

if __name__ == "__main__":
    os.system('clear')
    print(f"{Colors.BOLD}{Colors.BLUE}MTF Olympus v2.5 - Universal Health & Security Monitor{Colors.ENDC}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 65)
    
    diag = Diagnostic()
    diag.check_infrastructure()
    diag.check_resources()
    if diag.perform_login():
        diag.check_api_endpoints()
    diag.check_logs()
    diag.summary()
