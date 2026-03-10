from typing import Any, Type
from app.core.base_tool import BaseTool
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

    async def run_tool(self, input_data: Any, **kwargs) -> str:
        command = ""
        if isinstance(input_data, dict):
            command = input_data.get("command", "")
        elif isinstance(input_data, str):
            command = input_data

        if not command:
            return "Error: No command provided."

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
                try:
                    process.kill()
                except: pass
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
