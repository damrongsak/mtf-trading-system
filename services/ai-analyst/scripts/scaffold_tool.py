import sys
import os

TEMPLATE = '''from typing import Any, Optional, Type
import aiohttp
import logging
from app.core.config import settings
from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class {class_name}Input(BaseModel):
    # TODO: Define your input schema here
    symbol: str = Field(default="XAUUSD", description="Symbol to analyze")

class {class_name}Tool(BaseTool):
    name: str = "{tool_name}"
    description: str = "{description}"
    args_schema: Type[BaseModel] = {class_name}Input
    is_heavy: bool = False # Set to True if this tool does heavy IO

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        # 1. Normalize Input
        symbol = "XAUUSD"
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
        elif isinstance(input_data, str):
            symbol = input_data
        
        # 2. Logic
        logger.info(f"Executing {tool_name} for {{symbol}}")
        try:
            # async with aiohttp.ClientSession() as session:
            #     ...
            return f"Success: Result for {{symbol}}"
        except Exception as e:
            logger.error(f"{tool_name} error: {{e}}")
            return f"Error: {{str(e)}}"
'''

def scaffold(tool_name, description):
    filename = f"{tool_name}.py"
    path = os.path.join("app/tools", filename)
    
    if os.path.exists(path):
        print(f"Error: {path} already exists.")
        return

    class_name = "".join(x.capitalize() for x in tool_name.split("_"))
    content = TEMPLATE.format(
        class_name=class_name,
        tool_name=tool_name,
        description=description
    )
    
    with open(path, "w") as f:
        f.write(content)
    
    print(f"✅ Created {path} with institutional resilience standard.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/scaffold_tool.py <tool_name> '<description>'")
        sys.exit(1)
    
    scaffold(sys.argv[1], sys.argv[2])
