#!/usr/bin/env python3
import asyncio
import os
import sys
import uuid
import json
from datetime import datetime
from typing import Optional

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from rich.layout import Layout
from rich.style import Style
from rich.syntax import Syntax
from rich.text import Text
from rich.traceback import install

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style as PromptStyle
from prompt_toolkit.formatted_text import HTML

# Install rich traceback handler
install()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
AGENT_ENDPOINT = "/api/v1/ai/chat/sessions/message"
HEALTH_ENDPOINT = "/health"
USER_ID_FILE = ".cli_user_id"
HISTORY_FILE = ".cli_history"

class ChatApp:
    def __init__(self):
        self.console = Console()
        self.user_id = self.get_or_create_user_id()
        self.client = httpx.AsyncClient(timeout=120.0)
        self.running = True
        self.session = None # Delay init

    def get_or_create_user_id(self):
        if os.path.exists(USER_ID_FILE):
            with open(USER_ID_FILE, "r") as f:
                return f.read().strip()
        new_id = f"cli_user_{uuid.uuid4().hex[:8]}"
        with open(USER_ID_FILE, "w") as f:
            f.write(new_id)
        return new_id

    async def check_health(self) -> bool:
        try:
            resp = await self.client.get(f"{API_URL}{HEALTH_ENDPOINT}", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                # Status check logic
                return True
            return False
        except:
            return False

    def print_welcome(self):
        self.console.clear()
        
        # Title
        title = Text(" MTF Olympus AI Term ", style="bold white on blue")
        self.console.print(Panel(title, border_style="blue", expand=False))
        
        # Info
        self.console.print(f"[dim]User ID: {self.user_id}[/dim]")
        self.console.print(f"[dim]Gateway: {API_URL}[/dim]")
        self.console.print("[dim]Type [bold]/help[/bold] for commands. [bold]Alt+Enter[/bold] for new line.[/dim]\n")

    async def handle_command(self, text: str) -> bool:
        """Returns True if command handled, False if regular message"""
        cmd = text.strip().lower()
        if cmd in ["/quit", "/exit"]:
            self.running = False
            return True
        if cmd == "/clear":
            self.console.clear()
            self.print_welcome()
            return True
        if cmd == "/help":
            self.console.print(Panel(
                """
                [bold]Commands:[/bold]
                /quit, /exit  - Exit application
                /clear        - Clear screen
                /save         - Save transcript (TODO)
                
                [bold]Shortcuts:[/bold]
                Alt+Enter     - Multi-line input
                Up/Down       - History
                """,
                title="Help",
                border_style="yellow",
                expand=False
            ))
            return True
        return False

    async def run(self):
        # Initialize Prompt Session here
        self.session = PromptSession()
        
        self.print_welcome()
        
        # Connection check
        with self.console.status("[bold green]Connecting to AI Core...[/bold green]"):
            if not await self.check_health():
                self.console.print(f"[bold red]❌ Could not connect to {API_URL}[/bold red]")
                self.console.print("[yellow]Ensure 'docker compose up ai-analyst' is running.[/yellow]")
                # We don't exit, just warn
        
        self.console.print("[green]✓ Connected[/green]\n")

        while self.running:
            try:
                # Prompt Input
                # patch_stdout ensures prompt handling doesn't interfere with prints
                with patch_stdout():
                    user_input = await self.session.prompt_async(
                        HTML("<b><cyan>You</cyan></b>: "),
                        multiline=False # Allow simple enter for submission, M-Enter for newline is default in multiline=True but user prefers quick chat?
                        # Actually Web interfaces use Shift+Enter for newline. 
                        # prompt_toolkit multiline=True requires Alt+Enter to submit by default.
                        # Let's stick to multiline=False (Enter submits) for chat feel.
                        # If user wants multi-line, they can escape newline? or use editor.
                        # actually, many CLI chat apps use single line default.
                    )

                if not user_input.strip():
                    continue

                if await self.handle_command(user_input):
                    continue

                # Prepare Payload
                payload = {
                    "message": user_input,
                    "user_id": self.user_id
                }

                self.console.print()
                
                thoughts_content = None
                response_content = None
                error_msg = None
                start_time = datetime.now()

                # Spinner Context
                with Live(Spinner("dots", text="[italic cyan]Thinking...[/italic cyan]", style="cyan"), refresh_per_second=10, transient=True):
                    try:
                        response = await self.client.post(
                             f"{API_URL}{AGENT_ENDPOINT}", 
                             json=payload,
                             timeout=120.0
                        )
                        response.raise_for_status()
                        data = response.json()
                        
                        response_content = data.get("response", "")
                        thoughts_content = data.get("thoughts")
                        
                    except httpx.HTTPStatusError as e:
                        error_msg = f"[bold red]API Error {e.response.status_code}[/bold red]: {e.response.text}"
                    except Exception as e:
                        error_msg = f"[bold red]Request Failed[/bold red]: {str(e)}"
                        
                # ─── RENDER OUTPUT ──────────────────────────────────────────────
                
                elapsed = (datetime.now() - start_time).total_seconds()

                # 1. Thought Process (Collapsible)
                if thoughts_content:
                    # Create a distinct panel for thoughts
                    # We use a distinct style to separate "Thinking" from "Answer"
                    thought_panel = Panel(
                        Markdown(thoughts_content),
                        title=f"[bold blue]🧠 Reasoning ({elapsed:.1f}s)[/bold blue]",
                        border_style="blue",
                        expand=False,
                        padding=(1, 2)
                    )
                    self.console.print(thought_panel)
                    self.console.print() # Spacer

                # 2. Final Response
                if response_content:
                    self.console.print(Panel(
                        Markdown(response_content),
                        title="[bold violet]AI Analyst[/bold violet]",
                        border_style="violet",
                        expand=False
                    ))
                elif error_msg:
                    self.console.print(error_msg)
                
                self.console.print() # Bottom spacer

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error:[/red] {e}")

        self.console.print("[blue]Goodbye! 👋[/blue]")
        await self.client.aclose()

if __name__ == "__main__":
    app = ChatApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        pass
