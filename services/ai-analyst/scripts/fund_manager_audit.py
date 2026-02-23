import asyncio
import httpx
import logging
import os
import sys
from datetime import datetime

# Setup logging with Trace-ID support
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("fund-manager-audit")

API_URL = os.environ.get("API_URL", "http://api-gateway:8000")
USER_CREDENTIALS = {"username": "trader1", "password": "password123"}
REPORT_FILE = "fund_manager_report.md"

QUERIES = [
    # 1. Porfolio & Exposure
    "What is our current portfolio exposure and total risk value in USD?",
    # 2. Institutional Heatmap
    "Analyze XAUUSD liquidity depth. Where are the massive institutional buy/sell walls (Heatmap)?",
    # 3. COT Alignment
    "Are Non-Commercials increasing their long positions in Gold? (Perform a COT Audit)",
    # 4. Event Risk
    "The US CPI is releasing in 2 hours. What is the expected volatility and should we de-risk our current gold positions?",
    # 5. Precision Sizing
    "If I enter XAUUSD at 2150 with a stop at 2140, what is the maximum lot size for a $5k risk, and is the R:R acceptable for a Tier-1 setup?",
    # 6. Structural Analysis
    "Identify the most recent H1 Order Block that hasn't been mitigated. Is it a high-probability POI?",
    # 7. Options Focus
    "Provide a summary of the 'Max Pain' levels for XAUUSD option expiries this week.",
    # 8. Execution Health
    "Audit the current 'System Drift'. Are our strategies executing correctly or rejecting signals too frequently?",
    # 9. Cross-Asset Correlation
    "Calculate the correlation between Gold sentiment and recent S&P 500 volatility.",
    # 10. Multi-Timeframe Slim Data
    "Give me a 'Slim' JSON report of XAUUSD bias across 15m, 1h, and 4h timeframes.",
    # 11. Regime Detection
    "Is the current market regime 'Unstable'? Should we apply a risk multiplier of 0.5x?",
    # 12. Tactical Events
    "What are the top 3 high-impact news events for the remainder of the London session?",
    # 13. Equity Stability
    "Check account stability. Any abnormal drawdowns or equity spikes in the last 24h?",
    # 14. Integrated Plan
    "Generate a complete trading plan for XAUUSD based on current SMC confluence and institutional bias.",
    # 15. Telegram Risk Alert
    "Notify Telegram with a condensed risk report for all active strategies.",
    # 16. Imbalance Detection
    "Is there any bearish fair value gap (FVG) on the 1h timeframe that might act as a magnet for a correction?",
    # 17. Psychological Audit
    "Retrieve the last 5 journal entries regarding 'psychological drift' during gold volatility.",
    # 18. Strategy Verification (Backtest)
    "Backtest 'volatility_breakout' strategy on XAUUSD/H1 for the last 30 days. Report MDD and Sharpe Ratio.",
    # 19. Liquidity Sweep Verification
    "Is the current XAUUSD price at a 'Liquidity Sweep' level? Show reasoning.",
    # 20. The $100M Decision
    "Final assessment: If you were managing $100M, would you be long or flat on Gold right now, and why?"
]

async def get_auth_token():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/api/v1/auth/token", data=USER_CREDENTIALS)
        resp.raise_for_status()
        data = resp.json()
        return data["auth"]["access_token"], data["data"]["id"]

async def audit_query(token, user_id, query, index):
    request_id = f"auditor-pm-{index:02d}-{int(datetime.now().timestamp())}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": request_id
    }
    
    logger.info(f"[{index+1}/20] Auditing: {query}")
    start_time = asyncio.get_event_loop().time()
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{API_URL}/api/v1/ai/chat/sessions/message",
                json={"message": query, "user_id": user_id},
                headers=headers,
                timeout=180.0
            )
            duration = asyncio.get_event_loop().time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()["data"]
                answer = data.get("response") or data.get("answer") or "NO ANSWER"
                return {
                    "query": query,
                    "status": "PASS",
                    "id": request_id,
                    "duration": f"{duration:.2f}s",
                    "answer": answer
                }
            else:
                return {
                    "query": query,
                    "status": "FAIL",
                    "id": request_id,
                    "duration": f"{duration:.2f}s",
                    "answer": f"ERROR: {resp.status_code} - {resp.text}"
                }
        except Exception as e:
            return {
                "query": query,
                "status": "TIMEOUT/EXCEPTION",
                "id": request_id,
                "duration": "N/A",
                "answer": str(e)
            }

async def run_audit():
    logger.info("💼 Starting Hedge Fund Manager Global Audit...")
    token, user_id = await get_auth_token()
    
    results = []
    for i, q in enumerate(QUERIES):
        res = await audit_query(token, user_id, q, i)
        results.append(res)
        
    # Generate Report
    with open(REPORT_FILE, "w") as f:
        f.write("# Hedge Fund Manager Audit Report\n\n")
        f.write(f"**Date**: {datetime.now().isoformat()}\n")
        f.write(f"**Persona**: Institutional Fund Manager ($100M+ AUM)\n\n")
        
        f.write("## Executive Summary\n")
        passed = sum(1 for r in results if r['status'] == 'PASS')
        f.write(f"- **Queries Passed**: {passed}/20\n")
        f.write(f"- **Success Rate**: {(passed/20)*100:.1f}%\n\n")
        
        f.write("## Detailed Audit Log\n\n")
        for i, r in enumerate(results):
            f.write(f"### Q{i+1}: {r['query']}\n")
            f.write(f"- **Trace ID**: `{r['id']}`\n")
            f.write(f"- **Latency**: {r['duration']}\n")
            f.write(f"- **Status**: {'✅' if r['status'] == 'PASS' else '❌'} {r['status']}\n")
            f.write(f"- **Alpha Content**: \n\n{r['answer']}\n\n---\n\n")
            
    logger.info(f"🏆 Fund Manager Audit Completed. Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    asyncio.run(run_audit())
