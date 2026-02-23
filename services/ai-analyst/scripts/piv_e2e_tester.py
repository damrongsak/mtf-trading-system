import asyncio
import os
import sys
import httpx
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://api-gateway:8000") 
AGENT_ENDPOINT = "/api/v1/ai/chat/sessions/message"
LOGIN_ENDPOINT = "/api/v1/auth/token"

# Test Scenarios for PIV (Covering Scalping and Swing)
SCENARIOS = [
    {"name": "Standard Analysis", "query": "Analyze XAUUSD volatility structure (H1)."},
    {"name": "Scalping Context", "query": "Perform a PIV architectural audit for Gold on the M5 timeframe (Scalping)."},
    {"name": "Swing Context", "query": "Analyze Gold structural levels for a Swing trade on H4."},
    {"name": "Overextension Check", "query": "Is Gold overextended according to N-Bands volatility right now?"}
]

async def run_piv_e2e_tests():
    print("🚀 Starting PIV E2E Test Suite...")
    print(f"🔗 Target API: {API_URL}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
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
            token = token_data.get("access_token") 
            if not token and "auth" in token_data:
                token = token_data["auth"].get("access_token")
            
            if not token:
                print(f"❌ Login failed: No access_token found.")
                return
                
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Login successful.")
        except Exception as e:
            print(f"❌ Login error: {e}")
            return

        session_id = f"piv_e2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        report_lines = [
            "# PIV Volatility E2E Test Report\n",
            f"Generated: {datetime.now().isoformat()}",
            "---"
        ]
        
        for i, scenario in enumerate(SCENARIOS, 1):
            query = scenario["query"]
            name = scenario["name"]
            print(f"\n[{i}/{len(SCENARIOS)}] Testing: {name}")
            print(f"💬 Query: {query}")
            
            try:
                payload = {
                    "message": query,
                    "user_id": "trader1",
                    "thread_id": session_id
                }
                response = await client.post(f"{API_URL}{AGENT_ENDPOINT}", json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    inner_data = data.get("data", {})
                    answer = inner_data.get("response") or "No answer"
                    thoughts = inner_data.get("thoughts") or ""
                    
                    print(f"✅ Success.")
                    
                    # Verify tool usage in thoughts
                    tool_used = "volatility_structure_analysis" in (thoughts + answer)
                    
                    report_lines.append(f"### Test {i}: {name}")
                    report_lines.append(f"- **Query**: {query}")
                    report_lines.append(f"- **Tool Used**: {'✅ Yes' if tool_used else '❌ No'}")
                    report_lines.append(f"- **AI Response**:\n{answer}\n")
                else:
                    print(f"❌ Failed ({response.status_code})")
                    report_lines.append(f"### Test {i}: {name} (FAILED)")
                    report_lines.append(f"❌ Status {response.status_code}: {response.text}")
            except Exception as e:
                print(f"❌ Error: {e}")
                report_lines.append(f"### Test {i}: {name} (ERROR)")
                report_lines.append(f"❌ Exception: {e}")

        # Save report
        report_path = "piv_e2e_report.md"
        with open(report_path, "w") as f:
            f.writelines("\n".join(report_lines))
        print(f"\n🏁 Finished. Report: {report_path}")

if __name__ == "__main__":
    asyncio.run(run_piv_e2e_tests())
