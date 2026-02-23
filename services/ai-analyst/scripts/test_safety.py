import asyncio
import os
import sys
from google.genai import types

# Add the current directory to sys.path to allow importing app
sys.path.append(os.getcwd())

from app.services.gemini import GeminiClient
from app.core.config import settings

async def test_safety():
    print("--- Testing Gemini Safety Filters ---")
    client = GeminiClient()
    
    # A query that might trigger filters
    scary_query = "Give me a high leverage XAUUSD trading entry for the Asia session. I want to risk 50% of my account."
    
    # Test 1: Default (with our fix)
    print("\nTest 1: Default safety settings (BLOCK_NONE)...")
    try:
        resp = await client.generate_content(
            model=settings.gemini.flash_model_id,
            contents=[scary_query]
        )
        print(f"Response Text Size: {len(resp.get('text', ''))}")
        if not resp.get('text'):
            print("❌ Response is EMPTY (Blocked?)")
        else:
            print("✅ Response received.")
            print(f"Snippet: {resp.get('text')[:100]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Minimal safety settings
    print("\nTest 2: Minimal safety settings...")
    safety = [types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE")]
    try:
        resp = await client.generate_content(
            model=settings.gemini.flash_model_id,
            contents=[scary_query],
            safety_settings=safety
        )
        print(f"Response Text Size: {len(resp.get('text', ''))}")
        if not resp.get('text'):
            print("❌ Response is EMPTY")
        else:
            print("✅ Response received.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_safety())
