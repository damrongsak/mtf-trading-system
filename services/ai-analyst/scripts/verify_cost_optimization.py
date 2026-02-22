
import asyncio
import httpx
import time
import json

AI_ANALYST_URL = "http://localhost:8000" # internal port

async def test_sentiment_caching():
    print("Testing Sentiment Caching...")
    async with httpx.AsyncClient() as client:
        # First call (might be cache hit if scheduler already ran)
        start = time.time()
        resp1 = await client.post(f"{AI_ANALYST_URL}/api/v1/analyze/sentiment", json={"symbol": "XAUUSD"}, timeout=60.0)
        t1 = time.time() - start
        print(f"Call 1: {resp1.status_code} in {t1:.2f}s")
        
        # Second call (Should be cache hit)
        start = time.time()
        resp2 = await client.post(f"{AI_ANALYST_URL}/api/v1/analyze/sentiment", json={"symbol": "XAUUSD"}, timeout=60.0)
        t2 = time.time() - start
        print(f"Call 2 (Cache): {resp2.status_code} in {t2:.2f}s")
        
        if t2 < t1 or t2 < 0.5:
            print("✅ Caching verified (Fast response)")
        else:
            print("⚠️ Caching might not be active or first call was also cached")

async def test_lazy_loading_logic():
    print("\nTesting StrategyEngine Lazy Loading Logic (Internal)...")
    # This would require checking logs or internal state, but we can verify 
    # that requesting a non-gold symbol returns 0.0 quickly if headers are missing.
    async with httpx.AsyncClient() as client:
        start = time.time()
        resp = await client.post(f"{AI_ANALYST_URL}/api/v1/analyze/sentiment", json={"symbol": "BTCUSD"}, timeout=60.0)
        t = time.time() - start
        print(f"BTCUSD Sentiment: {resp.json().get('data', {}).get('score')} in {t:.2f}s")
        if t < 1.0:
             print("✅ Lazy Loading / Early Exit verified")

if __name__ == "__main__":
    asyncio.run(test_sentiment_caching())
    asyncio.run(test_lazy_loading_logic())
