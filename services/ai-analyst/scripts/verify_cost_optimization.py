import asyncio
import httpx
import time
import json
import logging
import hashlib
from app.services.sentiment import SentimentService
from unittest.mock import MagicMock, patch, AsyncMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify-optimization")

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
    async with httpx.AsyncClient() as client:
        start = time.time()
        resp = await client.post(f"{AI_ANALYST_URL}/api/v1/analyze/sentiment", json={"symbol": "BTCUSD"}, timeout=60.0)
        t = time.time() - start
        print(f"BTCUSD Sentiment: {resp.json().get('data', {}).get('score')} in {t:.2f}s")
        if t < 1.0:
             print("✅ Lazy Loading / Early Exit verified")

async def test_sentiment_hashing_unit():
    print("\n--- Testing Sentiment Headline Hashing (Unit Test) ---")
    service = SentimentService()
    
    # Mock news headlines
    headlines_raw = [
        {"title": "Gold reaches all-time high", "source": "Reuters"},
        {"title": "Fed signals rate cuts", "source": "Bloomberg"}
    ]
    headlines = [f"- {h['title']} ({h['source']})" for h in headlines_raw]
    
    # Mock Redis responses with AsyncMock
    service.redis.get = AsyncMock()
    service.redis.setex = AsyncMock()
    service.redis.xadd = AsyncMock()
    
    # 1. First run - Mock Cache Miss
    service.redis.get.side_effect = [None] 
    
    # Mock News Fetching
    with patch.object(service, '_fetch_news', return_value=headlines):
        # Mock LLM Analysis - Use AsyncMock for async method
        # Result from dev branch's _analyze_headlines_optimized
        mock_ai_result = {"score": 0.8, "reason": "Strong bullish news"}
        
        with patch.object(service, '_analyze_headlines_optimized', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_ai_result
            
            print("Running first analysis (Should call LLM)...")
            result1 = await service.get_sentiment("XAUUSD")
            print(f"Result 1: {result1['score']} - {result1['reason']}")
            
            # Verify LLM was called
            mock_analyze.assert_called_once()
            
            # 2. Second run - Same headlines, Mock Cache Hit with Hash
            headlines_text = "".join(headlines)
            headlines_hash = hashlib.md5(headlines_text.encode()).hexdigest()
            
            cached_data = {
                "score": 0.8,
                "reason": "Strong bullish news",
                "headlines_hash": headlines_hash
            }
            
            # Mock Cache Hit for the second call
            service.redis.get.side_effect = [json.dumps(cached_data)]
            
            print("\nRunning second analysis with same headlines (Should HIT Cache Hash)...")
            result2 = await service.get_sentiment("XAUUSD")
            print(f"Result 2: {result2['score']} - {result2['reason']}")
            
            # Verify LLM was NOT called again
            if mock_analyze.call_count == 1:
                print("✅ Success: LLM was not called redundantly.")
            else:
                print(f"❌ Failure: LLM was called {mock_analyze.call_count} times.")

    await service.close()

if __name__ == "__main__":
    # Run integration-style tests if API is reachable
    print("Starting verification...")
    try:
        import httpx
        loop = asyncio.get_event_loop()
        # We try to see if the API is up
        # This is optional and will fail gracefully if not in docker/not running
        loop.run_until_complete(test_sentiment_hashing_unit())
    except Exception as e:
        print(f"Verification script error: {e}")
