import asyncio
import os
import sys
import httpx
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000") 
AGENT_ENDPOINT = "/api/v1/ai/chat/sessions/message"
LOGIN_ENDPOINT = "/api/v1/auth/token"

# Test Scenarios (Concise for cost-optimization)
SCENARIOS = [
    "trader1 status? active fund/strategy?",
    "XAUUSD price (cTrader)?",
    "Gold H1 trend: bullish or bearish?",
    "Gold 15m OB/FVG status?",
    "Buy Gold, 1% risk. Lot size?",
    "XAUUSD sentiment summary?",
    "Trade signal for current session?",
    "Notify telegram: Account summary.",
    "Repeat risk at 2%. Lot size?",
    "Final check: all tools verified."
]

async def capture_service_logs(service_name: str, lines: int = 50):
    """Simple wrapper to get internal logs for the report."""
    try:
        cmd = f"docker logs --tail {lines} {service_name}"
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout.decode() + stderr.decode()
    except Exception as e:
        return f"Could not capture logs for {service_name}: {e}"

async def run_e2e_tests():
    print("🚀 Starting E2E Test Suite for AI Analyst...")
    print(f"🔗 Target API: {API_URL}")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        # 1. Login
        print("\n🔑 Logging in as 'trader1'...")
        try:
            resp = await client.post(
                f"{API_URL}{LOGIN_ENDPOINT}",
                data={"username": "trader1", "password": "password123"}
            )
            if resp.status_code != 200:
                print(f"❌ Login failed: {resp.status_code} - {resp.text}")
                return
            
            token_data = resp.json()
            # The API Gateway wraps the token in an 'auth' key
            token = token_data.get("access_token") 
            if not token and "auth" in token_data:
                token = token_data["auth"].get("access_token")
            
            if not token:
                print(f"❌ Login failed: No access_token found in response: {token_data}")
                return
                
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Login successful. Token obtained.")
        except Exception as e:
            print(f"❌ Login error: {e}")
            return

        session_id = f"e2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"🧵 Session ID: {session_id}")
        
        report_lines = [
            "# E2E Test Report - AI Analyst V3\n",
            "## 🛡️ Architecture & Auth Audit",
            "- **User Context**: `trader1` (Individual Trader)",
            "- **Auth Flow**: `chat_cli` -> `api-gateway` (JWT) -> `ai-analyst` -> `tools` (Header Forwarding)\n"
        ]
        
        for i, query in enumerate(SCENARIOS, 1):
            print(f"\n[{i}/10] Query: {query}")
            try:
                payload = {
                    "message": query,
                    "user_id": "trader1",
                    "thread_id": session_id
                }
                # Track request start for log correlation if possible
                response = await client.post(f"{API_URL}{AGENT_ENDPOINT}", json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    # The response is wrapped in success_response(data=result)
                    # result has 'response' and 'thoughts'
                    inner_data = data.get("data", {})
                    answer = inner_data.get("response") or "No answer found"
                    print(f"✅ Response received.")
                    
                    # Capture logs for specific tracing
                    ai_logs = await capture_service_logs("ai-analyst", 25)
                    gw_logs = await capture_service_logs("api-gateway", 15)
                    
                    # Check for Auth success in logs (simple keyword check)
                    auth_status = "✅ Header Forwarded" if "Authorization" in ai_logs or "Bearer" in ai_logs else "❓ Auth Trace Unclear"
                    if "401" in gw_logs or "403" in gw_logs:
                         auth_status = "❌ Auth Failure Detected in Gateway"

                    report_lines.append(f"### Test {i}: {query}")
                    report_lines.append(f"- **Auth Status**: {auth_status}")
                    report_lines.append(f"- **Question**: {query}")
                    report_lines.append(f"- **Answer**:\n{answer}\n")
                    report_lines.append("- **Service Logs (Architecture Trace)**:")
                    report_lines.append("```text\n--- AI-ANALYST (Internal Processing) ---\n" + ai_logs + "\n--- API-GATEWAY (Routing & Auth) ---\n" + gw_logs + "\n```\n")
                else:
                    report_lines.append(f"### Test {i}: {query} (FAILED)")
                    report_lines.append(f"❌ Status {response.status_code}: {response.text}")
            except Exception as e:
                print(f"❌ Error: {e}")
                report_lines.append(f"### Test {i}: {query} (ERROR)")
                report_lines.append(f"❌ Exception: {e}")

        # Save report
        with open("e2e_report.md", "w") as f:
            f.writelines("\n".join(report_lines))
        print(f"\n🏁 E2E Test Suite completed. Report saved to e2e_report.md")

if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
