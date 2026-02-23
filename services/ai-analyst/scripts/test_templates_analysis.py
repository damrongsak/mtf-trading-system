import asyncio
import httpx
import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()
API_URL = os.getenv("API_URL", "http://api-gateway:8000")
TOKEN = os.getenv("AUTH_TOKEN") # Should be provided or fetched

TEST_QUERIES = [
    "Analyze XAUUSD market structure (SMC) on H1/H4 timeframes.",
    "Analyze Gold liquidity depth. Where are the institutional buy/sell walls?",
    "Perform a COT Audit: Are Non-Commercials increasing long exposure?",
    "Synthesize SMC, COT, and Heatmap levels for a $100M decision on Gold."
]

async def run_audit():
    async with httpx.AsyncClient(timeout=180.0) as client:
        headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
        
        for q in TEST_QUERIES:
            console.print(f"\n[bold yellow]>>> Testing Template:[/bold yellow] {q}")
            payload = {
                "message": q,
                "user_id": "audit_user",
                "thread_id": f"audit_{os.urandom(4).hex()}"
            }
            
            try:
                resp = await client.post(f"{API_URL}/api/v1/ai/chat/sessions/message", json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    thoughts = data.get("thoughts", "No thoughts")
                    response = data.get("response", "No response")
                    
                    console.print(Panel(Markdown(thoughts), title="🧠 Reasoning Trace", border_style="blue"))
                    console.print(Panel(Markdown(response), title="🎯 AI Response", border_style="green"))
                else:
                    console.print(f"[red]Error {resp.status_code}: {resp.text}[/red]")
            except Exception as e:
                console.print(f"[red]Failed: {e}[/red]")

if __name__ == "__main__":
    if not TOKEN:
        console.print("[red]AUTH_TOKEN environment variable required.[/red]")
    else:
        asyncio.run(run_audit())
