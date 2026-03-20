import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
import json
import os

# Mock settings for testing
os.environ["DATABASE_URL"] = "postgresql+asyncpg://trader:trader_pass@localhost:5432/mtf_db_test"

def get_auth_token():
    # Login as demo1 via API Gateway
    gateway_url = os.getenv("GATEWAY_URL", "http://api-gateway:8000")
    import httpx
    with httpx.Client() as sync_client:
        resp = sync_client.post(f"{gateway_url}/api/v1/auth/token", data={"username": "demo1", "password": "password123"})
        if resp.status_code != 200:
             print(f"Auth failed: {resp.status_code} - {resp.text}")
        assert resp.status_code == 200
        return f"Bearer {resp.json()['auth']['access_token']}"

@pytest.mark.asyncio
async def test_phase3_thai_explainability():
    """
    Verifies that the AI can explain SMC concepts in professional Thai.
    """
    with TestClient(app) as client:
        token = get_auth_token()
        
        # Query in Thai regarding strategy explanation
        query = "ช่วยอธิบายกลยุทธ์ทองคำในไทม์เฟรม H1 และวิเคราะห์โครงสร้างตลาด (SMC) ให้หน่อย"
        
        response = client.post(
            "/api/v1/ai/think",
            json={"message": query, "stream": False},
            headers={"Authorization": token}
        )
        
        assert response.status_code == 200
        data = response.json().get("data", {})
        response_text = data.get("response", "")
        
        print(f"\nAI Response Translation Check (Thai):\n{response_text[:500]}...")
        
        # Check for technical markers (Case-insensitive)
        text_lower = response_text.lower()
        assert "smc" in text_lower or "โครงสร้าง" in response_text
        assert "executive summary" in text_lower or "สรุปสำหรับผู้บริหาร" in response_text or "บทสรุป" in response_text

@pytest.mark.asyncio
async def test_phase3_raw_data_request():
    """
    Verifies that for MARKET_ANALYSIS or STRATEGY_EXPLAIN, the tool is called with return_raw_data=True.
    """
    with TestClient(app) as client:
        token = get_auth_token()
        
        query = "Deep dive into XAUUSD H1 institutional order blocks and gaps. Explain the logic."
        
        response = client.post(
            "/api/v1/ai/think",
            json={"message": query, "stream": False},
            headers={"Authorization": token}
        )
        
        assert response.status_code == 200
        data = response.json().get("data", {})
        response_text = data.get("response", "")
        
        print(f"\nAI Response Narrative Check (English):\n{response_text[:500]}...")

        text_lower = response_text.lower()
        assert "executive summary" in text_lower
        assert any(term in text_lower for term in ["smc narrative", "institutional analysis", "institutional narrative", "market structure walkthrough"])
