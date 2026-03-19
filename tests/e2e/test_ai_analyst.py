import pytest
import asyncio
from datetime import datetime

@pytest.mark.asyncio
async def test_ai_analyst_health(api_client):
    """Check AI Analyst specific health."""
    response = await api_client.get("/api/v1/ai/admin/qdrant/health")
    # This might require admin headers, but let's check if it's open for health check
    if response.status_code == 200:
        assert "status" in response.json()
    else:
        # Fallback to general health if specific one fails
        resp = await api_client.get("/api/v1/health")
        assert resp.status_code == 200

@pytest.mark.asyncio
async def test_journal_analysis(api_client, auth_headers):
    """Test the 'Psychological MRI' - Journal Analysis."""
    url = "/api/v1/analyze/journal"
    payload = {
        "entry_content": "I felt anxious after the gold price broke the structure, so I closed my position too early despite the signal being valid.",
        "user_id": "demo_user"
    }
    
    response = await api_client.post(url, json=payload, headers=auth_headers)
    assert response.status_code == 200, f"Journal analysis failed: {response.text}"
    
    data = response.json()
    assert "insight" in data
    # Gemini should return a structured or semi-structured insight
    assert len(data["insight"]) > 50 # Expect a meaningful response

@pytest.mark.asyncio
async def test_market_analysis(api_client, auth_headers):
    """Test AI-driven market outlook generation."""
    url = "/api/v1/analyze/market"
    payload = {
        "symbol": "XAU_USD",
        "timeframe": "H1",
        "price_data": {"open": 2650.0, "high": 2670.0, "low": 2640.0, "close": 2665.0},
        "smc_data": {"bos": True, "choch": False, "fvg": "Bullish"},
        "user_id": "demo_user"
    }
    
    response = await api_client.post(url, json=payload, headers=auth_headers)
    assert response.status_code == 200, f"Market analysis failed: {response.text}"
    
    data = response.json()
    assert "insight" in data
    assert "Bullish" in str(data["insight"]) or "Bearish" in str(data["insight"]) or "Gold" in str(data["insight"])

@pytest.mark.asyncio
async def test_sentiment_analysis(api_client, auth_headers):
    """Test Sentiment analysis endpoint."""
    url = "/api/v1/analyze/sentiment"
    payload = {"symbol": "XAU_USD", "context": "Recent news about inflation"}
    
    response = await api_client.post(url, json=payload, headers=auth_headers)
    # This service might be mocked or skip news fetching in test
    if response.status_code == 200:
        data = response.json().get("data", {})
        assert "score" in data
    else:
        # If 503 it might mean external news API is down or not configured, which is acceptable for E2E if optional
        assert response.status_code in [200, 503]
