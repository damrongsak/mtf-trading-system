
import asyncio
import os
import sys

# Add app to path
sys.path.append(os.getcwd())

from app.core.config import settings
# Ensure API Key is set for Gemini
if not settings.GOOGLE_API_KEY:
    print("SKIPPING: API Key missing")
    sys.exit(0)

from app.services.semantic_cache import SemanticCache

async def verify_cache():
    print("--- Verifying Semantic Cache ---")
    
    # 1. Initialize
    cache = SemanticCache()
    # Provide a shorter timeout check if needed?
    
    if not cache.index:
        print("FAIL: Cache index not initialized (Check Redis)")
        return

    query = "What is the capital of Mars?"
    response = "Mars Capital City (Hypothetical)"
    
    # 2. Store
    print(f"Storing: {query} -> {response}")
    await cache.store(query, response)
    
    # Allow some time for async write? RedisVL is usually fast.
    await asyncio.sleep(1)
    
    # 3. Check Exact Match
    print("Checking Exact Match...")
    res = await cache.check(query)
    if res == response:
        print("PASS: Exact match found.")
    else:
        print(f"FAIL: Exact match not found. Got: {res}")
        
    # 4. Check Semantic Match
    query_sem = "tell me capital of mars"
    print(f"Checking Semantic Match: '{query_sem}'")
    res = await cache.check(query_sem, threshold=0.8) # Lower threshold for test
    if res == response:
        print("PASS: Semantic match found.")
    else:
        print(f"FAIL: Semantic match not found. Got: {res}")

if __name__ == "__main__":
    asyncio.run(verify_cache())
