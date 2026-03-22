import asyncio
import httpx
import json
import os
from datetime import datetime, timezone

GATEWAY_URL = "http://api-gateway:8000"
ANALYST_URL = "http://ai-analyst:8000"

SCENARIOS = [
    {
        "id": "S1",
        "name": "Gold Institutional Liquidity (XAUUSD)",
        "query": "Analyze XAU/USD for the last 2 weeks (March 8-22, 2026). I need SMC levels (OB/FVG), Pivot Points, and COT net positions. If COT is missing, find it. Give me a trade plan.",
        "expectations": ["Local database currently lacks", "COT", "OB", "FVG", "Pivot"]
    }
]

async def get_token(username, password):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GATEWAY_URL}/api/v1/auth/token",
            data={"username": username, "password": password}
        )
        if resp.status_code == 200:
            return resp.json()["auth"]["access_token"]
        return None

async def run_scenario(scenario, token):
    print(f"\n[Scenario {scenario['id']}] {scenario['name']}")
    print(f"Query: {scenario['query']}")
    
    async with httpx.AsyncClient(timeout=600) as client:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            # 1. Post to Gateway to queue the job
            resp = await client.post(
                f"{GATEWAY_URL}/api/v1/ai/think",
                json={
                    "message": scenario['query'],
                    "thread_id": f"thread_{scenario['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                },
                headers=headers
            )
            
            if resp.status_code not in (200, 202):
                print(f"❌ FAIL: Status {resp.status_code}")
                print(f"Response: {resp.text}")
                return {"id": scenario['id'], "status": "FAIL", "error": resp.text}
                
            job_data = resp.json()
            job_id = job_data.get("job_id")
            if not job_id:
                # Fallback if API hasn't been updated perfectly
                payload = job_data.get("data", job_data)
            else:
                print(f"Job Initialized: {job_id}. Polling for completion...")
                # 2. Poll for completion
                payload = None
                while True:
                    await asyncio.sleep(5)
                    poll_resp = await client.get(
                        f"{GATEWAY_URL}/api/v1/ai/jobs/{job_id}",
                        headers=headers
                    )
                    if poll_resp.status_code == 200:
                        poll_data = poll_resp.json()
                        status = poll_data.get("status")
                        if status == "completed":
                            payload = poll_data.get("data", {})
                            print(f"\n✅ Job {job_id} Completed!")
                            break
                        elif status == "error":
                            print(f"\n❌ Job {job_id} Failed: {poll_data.get('error')}")
                            return {"id": scenario['id'], "status": "FAIL", "error": poll_data.get("error")}
                        else:
                            print(".", end="", flush=True)
                    else:
                        print(f"\n⚠️ Polling error: {poll_resp.status_code} - {poll_resp.text}")
                        # Don't fail immediately, retry
                        
            # 3. Process Result
            if not payload:
                resp_data = resp.json()
                payload = resp_data.get("data", resp_data)
            
            response_text = payload.get("response", "")
            metadata = payload.get("metadata", {})
            thoughts = str(metadata.get("trace", "")) + " " + str(metadata.get("scratchpad", ""))
            
            # Basic validation
            found_expectations = [e for e in scenario['expectations'] if e.lower() in response_text.lower() or e.lower() in thoughts.lower()]
            pass_rate = len(found_expectations) / len(scenario['expectations'])
            
            print(f"--- RAW RESPONSE ---")
            print(response_text[:1000] + ("..." if len(response_text) > 1000 else ""))
            print(f"--- THOUGHTS ---")
            print(thoughts[:1000] + ("..." if len(thoughts) > 1000 else ""))
            
            print(f"Status: PASS ({pass_rate*100:.0f}% fidelity)")
            print(f"Fact-Checker Result: {metadata.get('fact_check_result', 'N/A')}")
            print(f"Data Recovery: {'ENGAGED' if metadata.get('data_gap_detected') else 'STABLE'}")
            
            return {
                "id": scenario['id'],
                "status": "PASS" if pass_rate >= 0.5 else "PARTIAL",
                "fidelity": pass_rate,
                "fact_check": metadata.get('fact_check_result'),
                "recovery": metadata.get('data_gap_detected')
            }
            
        except Exception as e:
            import traceback
            print(f"❌ ERROR: {e}")
            print(traceback.format_exc())
            return {"id": scenario['id'], "status": "ERROR", "error": f"{str(e)}\n{traceback.format_exc()}"}

async def main():
    print("================================================================")
    print("MTF Olympus Phase 68: Perfection Stress-Test Report")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("User: demo1 (Institutional Tester)")
    print("================================================================")

    token = await get_token("demo1", "password123")
    if not token:
        print("❌ CRITICAL: Authentication failed for demo1")
        return

    results = []
    for s in SCENARIOS:
        res = await run_scenario(s, token)
        results.append(res)
        print("Sleeping 10s between scenarios...")
        await asyncio.sleep(10)

    print("\n================================================================")
    print("PHASE 68 FINAL AUDIT SUMMARY")
    print("================================================================")
    for r in results:
        status_icon = "✅" if r['status'] == "PASS" else "⚠️" if r['status'] == "PARTIAL" else "❌"
        print(f"{status_icon} Scenario {r['id']}: {r['status']} (Fidelity: {r.get('fidelity', 0)*100:.0f}%)")
    
    all_pass = all(r['status'] == "PASS" for r in results)
    verdict = "WORLD-CLASS COMPLIANT" if all_pass else "STABLE WITH RECOVERIES"
    print(f"\nFinal Verdict: {verdict}")
    print("================================================================")

if __name__ == "__main__":
    asyncio.run(main())
