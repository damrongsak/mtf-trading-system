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
from prompt_toolkit.completion import WordCompleter
import random

# Import professional templates
try:
    from pro_templates import INSTITUTIONAL_TEMPLATES, PRO_TIPS
except ImportError:
    INSTITUTIONAL_TEMPLATES = []
    PRO_TIPS = []


# Install rich traceback handler
install()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
AGENT_ENDPOINT = "/api/v1/ai/chat/sessions/message"
AGENT_STREAM_ENDPOINT = "/api/v1/ai/chat/sessions/stream"
LOGIN_ENDPOINT = "/api/v1/auth/token"
HEALTH_ENDPOINT = "/health"
USER_ID_FILE = ".cli_user_id"
TOKEN_FILE = ".cli_token"
THREAD_ID_FILE = ".cli_thread_id"

class ChatApp:
    def __init__(self):
        self.console = Console()
        self.user_id = self.get_or_create_user_id()
        self.session_id = self.get_or_create_thread_id()
        self.auth_token = self.load_token()
        self.client = httpx.AsyncClient(timeout=300.0)
        self.running = True
        self.session = None # Delay init
        
        # Pro Features
        self.completer = WordCompleter(
            INSTITUTIONAL_TEMPLATES + ["/help", "/login", "/logout", "/new", "/session", "/clear", "/templates"],
            ignore_case=True,
            match_middle=True
        )
        self.current_tip = random.choice(PRO_TIPS) if PRO_TIPS else "Welcome to MTF Olympus"


    def get_or_create_user_id(self):
        if os.path.exists(USER_ID_FILE):
            with open(USER_ID_FILE, "r") as f:
                return f.read().strip()
        new_id = f"cli_user_{uuid.uuid4().hex[:8]}"
        with open(USER_ID_FILE, "w") as f:
            f.write(new_id)
        return new_id

    def get_or_create_thread_id(self):
        if os.path.exists(THREAD_ID_FILE):
            with open(THREAD_ID_FILE, "r") as f:
                return f.read().strip()
        new_id = f"sess_{uuid.uuid4().hex[:12]}"
        with open(THREAD_ID_FILE, "w") as f:
            f.write(new_id)
        return new_id

    def initialize_new_thread(self):
        new_id = f"sess_{uuid.uuid4().hex[:12]}"
        with open(THREAD_ID_FILE, "w") as f:
            f.write(new_id)
        self.session_id = new_id
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
        self.console.print(f"[dim]User ID: {self.user_id} | Session: {self.session_id}[/dim]")
        
        if self.auth_token:
            self.console.print("[bold green]Authenticated[/bold green]")
        else:
            self.console.print("[yellow]Guest Mode (Limited Access)[/yellow]")
            
        self.console.print("[dim]Type [bold]/help[/bold] for commands. [bold]Alt+Enter[/bold] for new line.[/dim]\n")

    def get_bottom_toolbar(self):
        """Returns the dynamic suggestion toolbar."""
        import html
        escaped_tip = html.escape(self.current_tip)
        return HTML(f'<ansiyellow fg="ansiblack"><b> PRO </b></ansiyellow> <ansicyan><i>{escaped_tip}</i></ansicyan>')

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
        if cmd == "/new":
            self.initialize_new_thread()
            self.console.clear()
            self.print_welcome()
            self.console.print("[bold green]Started a new conversation session.[/bold green]")
            return True
        if cmd == "/session":
            self.console.print(f"[bold cyan]Current Session Details:[/bold cyan]")
            self.console.print(f"User ID: {self.user_id}")
            self.console.print(f"Thread ID: {self.session_id}")
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
        if cmd == "/templates":
            self.console.print(Panel(
                "\n".join([f"• {t}" for t in INSTITUTIONAL_TEMPLATES]),
                title="[bold cyan]Institutional Query Templates[/bold cyan]",
                border_style="cyan",
                expand=False
            ))
            return True
        if cmd == "/help":

            self.console.print(Panel(
                """
                [bold]Commands:[/bold]
                /login        - Authenticate
                /logout       - Clear session
                /new          - Start a fresh interaction (clear AI memory)
                /session      - View current thread info
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
                # Rotate tip for each turn
                if PRO_TIPS:
                    self.current_tip = random.choice(PRO_TIPS)

                # Prompt Input
                with patch_stdout():
                    user_input = await self.session.prompt_async(
                        HTML("<b><cyan>You</cyan></b>: "),
                        multiline=False,
                        is_password=False,
                        completer=self.completer,
                        bottom_toolbar=self.get_bottom_toolbar
                    )


                if not user_input.strip():
                    continue

                if await self.handle_command(user_input):
                    continue

                # Prepare Payload
                payload = {
                    "message": user_input,
                    "user_id": self.user_id,
                    "thread_id": self.session_id
                }
                
                headers = {}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"

                self.console.print()
                
                thoughts_content = None
                response_content = None
                error_msg = None
                start_time = datetime.now()

                # Spinner Context (deprecated - nested in Live)
                with Live(Panel(Text("Thinking...", style="italic cyan"), title="[bold violet]MTF Olympus AI[/bold violet]", border_style="violet", expand=False), refresh_per_second=10, transient=True) as live:
                    try:
                        async with self.client.stream(
                            "POST",
                            f"{API_URL}{AGENT_STREAM_ENDPOINT}",
                            json=payload,
                            headers=headers,
                            timeout=300.0
                        ) as response:
                            if response.status_code == 401 or response.status_code == 403:
                                error_msg = "[bold red]Authentication Failed (401). Please /login again.[/bold red]"
                                # Invalidate token
                                if os.path.exists(TOKEN_FILE):
                                    os.remove(TOKEN_FILE)
                                self.auth_token = None
                            else:
                                response.raise_for_status()
                                async for line in response.aiter_lines():
                                    if not line:
                                        continue
                                    
                                    try:
                                        event = json.loads(line)
                                        event_type = event.get("type")
                                        
                                        if event_type == "status":
                                            current_status = event.get("content", "")
                                        elif event_type == "token":
                                            response_content += event.get("content", "")
                                        elif event_type == "tool_start":
                                            current_status = f"Using tool: {event.get('tool')}..."
                                        elif event_type == "final":
                                            response_content = event.get("response") or response_content
                                            thoughts_content = event.get("thoughts") or ""
                                        elif event_type == "error":
                                            error_msg = f"[bold red]AI Error[/bold red]: {event.get('content')}"
                                            break
                                        
                                        # Update Live Display
                                        elapsed = (datetime.now() - start_time).total_seconds()
                                        
                                        display_text = Text()
                                        if response_content:
                                            # Convert Markdown to Rich for rendering
                                            md = Markdown(response_content)
                                            # We just show the raw markdown during stream for performance, or partial MD
                                            # For simplicity in CLI, we'll just show the text and re-render final later
                                            display_text.append(response_content)
                                        else:
                                            display_text.append(current_status, style="italic cyan")

                                        live.update(Panel(
                                            display_text,
                                            title=f"[bold violet]MTF Olympus AI ({elapsed:.1f}s)[/bold violet]",
                                            border_style="violet",
                                            expand=False
                                        ))
                                        
                                    except Exception as e:
                                        self.console.print(f"[dim red]Stream Parse Error: {e}[/dim red]")

                    except httpx.HTTPStatusError as e:
                        try:
                            await e.response.aread()
                            error_msg = f"[bold red]API Error {e.response.status_code}[/bold red]: {e.response.text}"
                        except:
                            error_msg = f"[bold red]API Error {e.response.status_code}[/bold red]"
                    except Exception as e:
                        error_msg = f"[bold red]Request Failed[/bold red]: {str(e)}"
                        
                # ─── FINAL RENDER ──────────────────────────────────────────────
                
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
