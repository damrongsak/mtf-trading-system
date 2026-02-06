import asyncio
import os
import sys
from pathlib import Path

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from google import genai

async def main():
    print("🔍 Listing Available Models...")
    
    try:
        from google import genai
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # New SDK supports list_models() through the models module
        print("\n--- Available Models ---")
        for m in client.models.list(config={"page_size": 100}):
            try:
                print(f"Model: {m.name}")
                # Try to print path if distinct
                # print(f"  Path: {m.name}") 
            except:
                pass

    except Exception as e:
        print(f"❌ Failed to list models: {e}")

if __name__ == "__main__":
    asyncio.run(main())
