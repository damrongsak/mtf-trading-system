from typing import Dict, Any, Callable
from langchain_core.tools import Tool, StructuredTool
from pydantic import create_model
import json

class MCPToolAdapter:
    """
    Adapter to convert Model Context Protocol (MCP) tool definitions
    into LangChain-compatible tools that UniversalAgent can use.
    """
    
    @staticmethod
    def create_tool(name: str, description: str, schema: Dict[str, Any], execute_fn: Callable) -> StructuredTool:
        """
        Creates a LangChain StructuredTool from an MCP schema.
        
        Args:
            name: Tool name
            description: Tool description
            schema: JSON Schema of arguments (properties)
            execute_fn: Async function to call
        """
        # 1. Dynamic Pydantic Model from JSON Schema
        # Simplified: We assume schema is a dict of {arg_name: type} or basic JSON schema 'properties'
        fields = {}
        for arg, props in schema.get("properties", {}).items():
            # Map JSON types to Python types (Simplified)
            py_type = str
            if props.get("type") == "integer":
                py_type = int
            elif props.get("type") == "number":
                py_type = float
            elif props.get("type") == "boolean":
                py_type = bool
            
            fields[arg] = (py_type, ...)
            
        args_model = create_model(f"{name}Schema", **fields)
        
        # 2. Wrapper Function
        async def wrapper(**kwargs):
            return await execute_fn(**kwargs)
            
        # 3. Create Tool
        return StructuredTool.from_function(
            func=None,
            coroutine=wrapper,
            name=name,
            description=description,
            args_schema=args_model
        )

    @staticmethod
    def load_from_json(json_def: str, handler_map: Dict[str, Callable]) -> StructuredTool:
        """
        Load a tool from a JSON definition string.
        """
        data = json.loads(json_def)
        return MCPToolAdapter.create_tool(
            name=data["name"],
            description=data["description"],
            schema=data["inputSchema"],
            execute_fn=handler_map[data["name"]]
        )
