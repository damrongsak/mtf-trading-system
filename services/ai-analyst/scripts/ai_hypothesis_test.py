import asyncio
import os
import httpx
import json
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://api-gateway:8000") 
AGENT_ENDPOINT = "/api/v1/ai/chat/sessions/message"
LOGIN_ENDPOINT = "/api/v1/auth/token"

# Test Hypotheses
HYPOTHESES = [
    {
        "id": "H1",
        "title": "Multi-Timeframe Alignment",
        "query": "Analyze XAUUSD on M15 and compare it with H1 structure. Are they aligned?",
        "success_criteria": "Agent fetches both M15 and H1 data and provides a comparative analysis."
    },
    {
        "id": "H2",
        "title": "SMC Setup Identification (M15)",
        "query": "Are there any bullish Order Blocks on Gold M15 right now?",
        "success_criteria": "Agent uses smc_technical_analysis for M15 and identifies specific OBs if they exist."
    },
    {
        "id": "H3",
        "title": "Predictor Integration (M15)",
        "query": "What is the 5-step price forecast for XAUUSD on M15?",
        "success_criteria": "Agent calls the predictor tool with M15 timeframe and reports the forecast prices."
    },
    {
        "id": "H4",
        "title": "Trading Plan Generation",
        "query": "Generate a buy trading plan for Gold M15 with 1.5% risk.",
        "success_criteria": "Agent generates a plan with Entry, SL, TP, and calculated Lot Size for M15."
    },
    {
        "id": "H5",
        "title": "Market Sentiment & Regime",
        "query": "What is the current market regime for XAUUSD and how is the sentiment affecting it?",
        "success_criteria": "Agent fetches regime and sentiment data and explains their relationship."
    },
    {
        "id": "H6",
        "title": "RAG + Live Data Synthesis",
        "query": "Explain the SMC concept of a 'Change of Character' (CHoCH) and identify if one has occurred on XAUUSD recently.",
        "success_criteria": "Agent retrieves CHoCH definition from RAG and checks live candles for the pattern."
    },
    {
        "id": "H7",
        "title": "External News Integration",
        "query": "Search for recent news about US Inflation and explain how it might impact the current Gold M15 setup.",
        "success_criteria": "Agent performs a web search and links news events to the Gold technical setup."
    },
    {
        "id": "H8",
        "title": "Account-Aware Risk Reasoning",
        "query": "Check my account status and tell me if I have enough margin to open a 0.5 lot position on XAUUSD.",
        "success_criteria": "Agent fetches account equity/margin and provides a yes/no answer based on typical margin requirements."
    },
    {
        "id": "H9",
        "title": "Cross-Symbol Comparison",
        "query": "Compare XAUUSD and EURUSD H1 trends. Which one shows a clearer SMC structure?",
        "success_criteria": "Agent fetches SMC data for both symbols and provides a comparative judgment."
    },
    {
        "id": "H10",
        "title": "System Diagnostic Execution",
        "query": "Run a system health check. Are the data pipelines and predictor services functioning for M15 data?",
        "success_criteria": "Agent uses diagnostic tools or infers health from tool performance to answer."
    }
]

async def run_hypothesis_tests():
    print("🔬 Starting AI Analyst Hypothesis Testing...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. Login
        print("🔑 Authenticating...")
        try:
            resp = await client.post(
                f"{API_URL}{LOGIN_ENDPOINT}",
                data={"username": "trader1", "password": "password123"}
            )
            token = resp.json().get("access_token") or resp.json().get("auth", {}).get("access_token")
            if not token:
                print("❌ Auth Failed")
                return
            headers = {"Authorization": f"Bearer {token}"}
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return

        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = []

        for h in HYPOTHESES:
            print(f"\n[{h['id']}] {h['title']}")
            print(f"  Query: {h['query']}")
            
            try:
                start_time = datetime.now()
                response = await client.post(
                    f"{API_URL}{AGENT_ENDPOINT}",
                    json={"message": h["query"], "user_id": "trader1", "thread_id": session_id},
                    headers=headers
                )
                duration = (datetime.now() - start_time).total_seconds()
                
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    answer = data.get("response", "EMPTY")
                    thoughts = data.get("thoughts", "No thoughts recorded")
                    print(f"  ✅ Completed in {duration:.1f}s")
                    
                    results.append({
                        "id": h["id"],
                        "title": h["title"],
                        "query": h["query"],
                        "success_criteria": h["success_criteria"],
                        "status": "PASS" if "Error" not in answer and "unavailable" not in answer.lower() else "FAIL/UNKNOWN",
                        "duration": duration,
                        "answer": answer,
                        "thoughts": thoughts
                    })
                else:
                    print(f"  ❌ Failed: {response.status_code}")
                    results.append({
                        "id": h["id"],
                        "title": h["title"],
                        "status": "ERROR",
                        "error": response.text
                    })
            except Exception as e:
                print(f"  ❌ Exception: {e}")

        # Generate Result Report
        report_path = "ai_hypothesis_report.md"
        with open(report_path, "w") as f:
            f.write("# 🔬 AI Analyst Hypothesis Test Report\n\n")
            f.write(f"**Date**: {datetime.now().isoformat()}\n")
            f.write(f"**Session ID**: {session_id}\n\n")
            
            f.write("## 📊 Summary Table\n\n")
            f.write("| ID | Hypothesis | Status | Duration | Result Analysis |\n")
            f.write("|:---|:---|:---|:---|:---|\n")
            for r in results:
                status_emoji = "✅" if r.get("status") == "PASS" else "❌"
                f.write(f"| {r['id']} | {r['title']} | {status_emoji} {r.get('status')} | {r.get('duration', 0):.1f}s | [See Detail](#{r['id'].lower()}) |\n")
            
            f.write("\n## 📝 Detailed Results\n\n")
            for r in results:
                f.write(f"### <a name=\"{r['id'].lower()}\"></a>[{r['id']}] {r['title']}\n")
                f.write(f"- **Query**: {r.get('query')}\n")
                f.write(f"- **Success Criteria**: {r.get('success_criteria')}\n")
                f.write(f"- **AI Response**:\n\n{r.get('answer')}\n\n")
                f.write(f"- **Reasoning (Thoughts)**:\n\n> {r.get('thoughts')}\n\n")
                f.write("---\n")

        print(f"\n🏁 Finished. Report saved to {report_path}")

if __name__ == "__main__":
    asyncio.run(run_hypothesis_tests())
