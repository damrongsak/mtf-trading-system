import asyncio
import json
import logging
from app.services.sentiment import SentimentService
from unittest.mock import MagicMock, patch, AsyncMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify-optimization")

async def test_sentiment_hashing():
    print("\n--- Testing Sentiment Headline Hashing ---")
    service = SentimentService()
    
    # Mock news headlines
    headlines = [
        {"title": "Gold reaches all-time high", "source": "Reuters"},
        {"title": "Fed signals rate cuts", "source": "Bloomberg"}
    ]
    
    # Mock Redis responses with AsyncMock
    service.redis.get = AsyncMock()
    service.redis.setex = AsyncMock()
    service.redis.xadd = AsyncMock()
    
    # 1. First run - Mock Cache Miss
    # Redis get should return None for the first call (cache miss)
    service.redis.get.side_effect = [None] 
    
    # Mock News Fetching
    with patch.object(service, '_fetch_news', return_value=[f"- {h['title']} ({h['source']})" for h in headlines]):
        # Mock LLM Analysis - Use AsyncMock for async method
        mock_response = MagicMock()
        mock_response.content = '{"score": 0.8, "reason": "Strong bullish news"}'
        
        with patch('app.services.sentiment.ChatGoogleGenerativeAI.ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_response
            
            print("Running first analysis (Should call LLM)...")
            result1 = await service.get_sentiment("XAUUSD")
            print(f"Result 1: {result1['score']} - {result1['reason']}")
            
            # Verify LLM was called
            mock_ainvoke.assert_called_once()
            
            # 2. Second run - Same headlines, Mock Cache Hit with Hash
            # Calculate hash for verification
            import hashlib
            headlines_text = "".join([f"- {h['title']} ({h['source']})" for h in headlines])
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
            if mock_ainvoke.call_count == 1:
                print("✅ Success: LLM was not called redundantly.")
            else:
                print(f"❌ Failure: LLM was called {mock_ainvoke.call_count} times.")

    await service.close()

if __name__ == "__main__":
    asyncio.run(test_sentiment_hashing())
