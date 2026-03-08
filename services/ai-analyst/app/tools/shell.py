from typing import Type, Optional, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import subprocess
import asyncio
import logging

logger = logging.getLogger(__name__)

class ShellInput(BaseModel):
    command: str = Field(description="The bash command to execute")

class ShellCommandTool(BaseTool):
    name: str = "shell_command"
    description: str = (
        "Execute a bash command in the local environment. "
        "Use for file operations (ls, cat, find), system checks, or other OS tasks. "
        "Output is truncated to 5000 chars for token safety."
    )
    args_schema: Type[BaseModel] = ShellInput

    def _run(self, command: str) -> str:
        # We prefer async execution in this service, but provide sync fallback
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # This is tricky in a running event loop, but for sync call we hope for the best
            # or just use subprocess sync
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=30)
            return (stdout + stderr)[:5000]
        else:
            return loop.run_until_complete(self._arun(command))

    async def _arun(self, command: str) -> str:
        """Execute bash command asynchronously."""
        try:
            # 30s timeout to prevent hanging
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
            except asyncio.TimeoutError:
                process.kill()
                return "Error: Command timed out after 30 seconds."

            result = stdout.decode().strip()
            error = stderr.decode().strip()

            output = result if result else error
            if not output:
                return "Command executed successfully (no output)."
            
            # Truncate for token safety
            if len(output) > 5000:
                output = output[:5000] + "\n... (truncated)"
            
            return output
        except Exception as e:
            logger.error(f"ShellCommandTool error: {e}")
            return f"Error: {str(e)}"
