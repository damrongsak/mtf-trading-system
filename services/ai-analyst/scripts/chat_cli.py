#!/usr/bin/env python3
import asyncio
import os
import sys
import uuid
from datetime import datetime

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.emoji import Emoji
from rich import print as rprint

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
AGENT_ENDPOINT = "/api/v1/ai/chat/sessions/message"
HEALTH_ENDPOINT = "/health"
USER_ID_FILE = ".cli_user_id"

console = Console()

def get_or_create_user_id():
    """Persist user ID across sessions for long-term memory testing."""
    if os.path.exists(USER_ID_FILE):
        with open(USER_ID_FILE, "r") as f:
            return f.read().strip()
    
    new_id = f"cli_user_{uuid.uuid4().hex[:8]}"
    with open(USER_ID_FILE, "w") as f:
        f.write(new_id)
    return new_id

async def check_health(client: httpx.AsyncClient):
    """Verify service is reachable and agents are active."""
    try:
        resp = await client.get(f"{API_URL}{HEALTH_ENDPOINT}", timeout=2.0)
        resp.raise_for_status()
        data = resp.json()
        
        status_table = []
        agents = data.get("agents", {})
        
        if data.get("status") == "ok":
            rprint(Panel(f"[green]Connected to AI Analyst Service[/green]\n[dim]Gateway: {API_URL}[/dim]", expand=False))
            
            # Simple status check
            advisor_status = agents.get("strategy_advisor", "unknown")
            if advisor_status != "active":
                rprint(f"[yellow]⚠️  Warning: Strategy Advisor is {advisor_status}[/yellow]")
            else:
                 rprint(f"[green]✓ Strategy Advisor Ready[/green]")
            return True
        else:
            rprint(f"[red]Service Status: {data.get('status')}[/red]")
            return False
            
    except Exception as e:
        rprint(f"[bold red]❌ Could not connect to {API_URL}[/bold red]")
        rprint(f"[dim]Error: {e}[/dim]")
        rprint("\n[yellow]Tip: Ensure the service is running (docker compose up ai-analyst)[/yellow]")
        return False

async def main():
    # Header
    console.clear()
    console.rule("[bold blue]MTF Olympus AI Term[/bold blue]")
    
    user_id = get_or_create_user_id()
    rprint(f"[dim]User ID: {user_id}[/dim]\n")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Health Check
        if not await check_health(client):
            sys.exit(1)
            
        console.print()
        console.print("[bold]Commands:[/bold] [green]/quit[/green], [green]/clear[/green], [green]/context <text>[/green]")
        console.print("Start chatting with your Hedge Fund Co-Pilot...\n")

        # 2. Chat Loop
        while True:
            try:
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
                
                # Command Handling
                if user_input.lower() in ["/quit", "/exit"]:
                    rprint("[blue]Goodbye! 👋[/blue]")
                    break
                
                if user_input.lower() == "/clear":
                    console.clear()
                    continue
                
                if not user_input.strip():
                    continue

                # Prepare Payload
                payload = {
                    "message": user_input,
                    "user_id": user_id,
                    "context_code": None, # Future: read from file
                    "image_b64": None     # Future: read from file
                }

                # 3. Request with Spinner
                console.print() # spacer
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                ) as progress:
                    task = progress.add_task("[cyan]Thinking (CoT-RAG)...[/cyan]", total=None)
                    
                    try:
                        response = await client.post(
                            f"{API_URL}{AGENT_ENDPOINT}", 
                            json=payload
                        )
                        response.raise_for_status()
                        data = response.json()
                        
                        agent_response = data.get("response", "")
                        
                        # 4. Render Response
                        console.print(Panel(
                            Markdown(agent_response),
                            title="[bold violet]AI Analyst[/bold violet]",
                            border_style="violet"
                        ))
                        console.print()
                        
                    except httpx.HTTPStatusError as e:
                        rprint(f"[bold red]API Error {e.response.status_code}[/bold red]: {e.response.text}")
                    except Exception as e:
                        rprint(f"[bold red]Request Failed[/bold red]: {str(e)}")

            except KeyboardInterrupt:
                rprint("\n[blue]Goodbye! 👋[/blue]")
                break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
