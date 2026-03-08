import sys
import io
import pandas as pd
import numpy as np
import math
import statistics
import logging
from typing import Any, Optional, Type, Dict
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class PythonInput(BaseModel):
    code: str = Field(description="The Python code to execute")

class PythonInterpreterTool(BaseTool):
    name: str = "python_interpreter"
    description: str = (
        "Execute Python code locally for calculations, data analysis, or complex logic. "
        "Has access to 'pandas' (as pd), 'numpy' (as np), 'math', and 'statistics'. "
        "Pre-defined 'df' or data structures should be created within the code. "
        "Capture output using print()."
    )
    args_schema: Type[BaseModel] = PythonInput

    def _run(self, code: str) -> str:
        """Execute Python code and capture stdout."""
        # Redirect stdout to capture print statements
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        # Define restricted globals
        safe_globals = {
            "pd": pd,
            "np": np,
            "math": math,
            "statistics": statistics,
            "__builtins__": __builtins__
        }

        try:
            # Execute the code
            exec(code, safe_globals)
            sys.stdout = old_stdout
            output = redirected_output.getvalue().strip()
            return output if output else "Code executed successfully (no output)."
        except Exception as e:
            sys.stdout = old_stdout
            logger.error(f"PythonInterpreterTool error: {e}")
            return f"Error: {str(e)}"

    async def _arun(self, code: str) -> str:
        """Async execution (delegates to sync)."""
        return self._run(code)
