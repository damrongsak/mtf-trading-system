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
LOGIN_ENDPOINT = "/api/v1/auth/token"
HEALTH_ENDPOINT = "/health"
USER_ID_FILE = ".cli_user_id"
TOKEN_FILE = ".cli_token"

class ChatApp:
    def __init__(self):
        self.console = Console()
        self.user_id = self.get_or_create_user_id()
        self.auth_token = self.load_token()
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

    def load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                return f.read().strip()
        return None

    def save_token(self, token):
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
        self.auth_token = token

    async def login(self):
        self.console.print(Panel("🔒 **Authentication Required**\nPlease log in to access your account data.", style="yellow"))
        
        while True:
            username = await self.session.prompt_async(HTML("Username: "))
            password = await self.session.prompt_async(HTML("Password: "), is_password=True)
            
            with self.console.status("[bold green]Logging in...[/bold green]"):
                try:
                    # Standard OAuth2 Form Request
                    data = {"username": username, "password": password}
                    resp = await self.client.post(f"{API_URL}{LOGIN_ENDPOINT}", data=data)
                    
                    if resp.status_code == 200:
                        token_data = resp.json()
                        token = None
                        if "auth" in token_data:
                            token = token_data["auth"]["access_token"]
                            if "data" in token_data:
                                self.user_id = token_data["data"]["id"]
                                with open(USER_ID_FILE, "w") as f:
                                    f.write(self.user_id)
                        else:
                             token = token_data.get("access_token")
                             
                        if token:
                            self.save_token(token)
                            self.console.print("[green]✓ Login Successful[/green]")
                            return True
                        else:
                             self.console.print(f"[red]Login Successful but no token found in response.[/red]")
                    else:
                        self.console.print(f"[red]Login Failed ({resp.status_code}): {resp.text}[/red]")
                except Exception as e:
                    self.console.print(f"[red]Connection Error: {e}[/red]")
            
            retry = await self.session.prompt_async("Try again? (y/n): ")
            if retry.lower() != 'y':
                return False

    async def check_health(self) -> bool:
        try:
            resp = await self.client.get(f"{API_URL}{HEALTH_ENDPOINT}", timeout=2.0)
            return resp.status_code == 200
        except:
            return False

    def print_welcome(self):
        self.console.clear()
        
        # Title
        title = Text(" MTF Olympus AI Term ", style="bold white on blue")
        self.console.print(Panel(title, border_style="blue", expand=False))
        
        # Info
        self.console.print(f"[dim]User ID: {self.user_id}[/dim]")
        
        if self.auth_token:
            self.console.print("[bold green]Authenticated[/bold green]")
        else:
            self.console.print("[yellow]Guest Mode (Limited Access)[/yellow]")
            
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
        if cmd == "/login":
            await self.login()
            self.print_welcome()
            return True
        if cmd == "/logout":
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            self.auth_token = None
            self.console.print("[yellow]Logged out.[/yellow]")
            return True
        if cmd == "/help":
            self.console.print(Panel(
                """
                [bold]Commands:[/bold]
                /login        - Authenticate
                /logout       - Clear session
                /quit, /exit  - Exit application
                /clear        - Clear screen
                
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
        
        # Auto-login check if no token
        if not self.auth_token:
            self.console.print("[dim]Tip: Type /login to access account data.[/dim]")

        self.console.print("[green]✓ Connected[/green]\n")

        while self.running:
            try:
                # Prompt Input
                with patch_stdout():
                    user_input = await self.session.prompt_async(
                        HTML("<b><cyan>You</cyan></b>: "),
                        multiline=False,
                        is_password=False
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
                
                headers = {}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"

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
                             headers=headers,
                             timeout=120.0
                        )
                        
                        if response.status_code == 401 or response.status_code == 403:
                            error_msg = "[bold red]Authentication Failed (401). Please /login again.[/bold red]"
                            # Invalidate token
                            if os.path.exists(TOKEN_FILE):
                                os.remove(TOKEN_FILE)
                            self.auth_token = None
                        else:
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
                        title="[bold violet]MTF Olympus AI[/bold violet]",
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
