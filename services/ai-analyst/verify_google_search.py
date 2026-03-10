import asyncio
import os
import sys

# Add the mtf-trading-system directory to the path so we can import from services
sys.path.append("/home/dan/workspace/mtf-trading-system/services/ai-analyst")

from app.tools.search import GoogleSearchTool
from app.core.config import settings

async def main():
    print(f"SERPAPI_API_KEY configured: {'Yes' if settings.SERPAPI_API_KEY else 'No'}")
    
    tool = GoogleSearchTool()
    query = "latest news about gold price today"
    
    print(f"\n--- Testing GoogleSearchTool with query: '{query}' ---")
    try:
        result = await tool.arun(query)
        print("\n--- Result ---")
        print(result)
        print("--------------")
    except Exception as e:
        print(f"Error executing search: {e}")

if __name__ == "__main__":
    asyncio.run(main())
