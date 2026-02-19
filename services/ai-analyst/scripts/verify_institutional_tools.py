import asyncio
import os
import sys
from typing import Any

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.tools import ToolRegistry
from app.services.rag import RAGService

class MockRAG:
    async def search_documentation(self, q): return []

async def test_tools():
    print("🚀 Verifying AI Analyst Institutional Tools...")
    
    # Initialize Registry with mock RAG
    registry = ToolRegistry(rag_service=MockRAG())
    
    tools_to_test = ["cot_analyst", "liquidity_heatmap", "open_interest"]
    
    for tool_name in tools_to_test:
        print(f"\n--- Testing Tool: {tool_name} ---")
        tool = registry.get_tool(tool_name)
        if not tool:
            print(f"❌ Tool {tool_name} not found in registry!")
            continue
            
        try:
            # We skip auth_token for local testing if services are up and don't require it
            # or if they handle missing auth gracefully
            result = await tool.run(input_data={"symbol": "XAUUSD"})
            print(result)
        except Exception as e:
            print(f"❌ Error running {tool_name}: {e}")

if __name__ == "__main__":
    asyncio.run(test_tools())
