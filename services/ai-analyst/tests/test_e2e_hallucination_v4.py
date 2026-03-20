import pytest
import requests
import json
import os
import time

# Configuration
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
AUTH_URL = os.environ.get("AUTH_URL", "http://api-gateway:8000/api/v1/auth/token")
TEST_USER = "demo1"
TEST_PASS = "password123"

class TestClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.token = None
    
    def authenticate(self, username=TEST_USER, password=TEST_PASS):
        response = requests.post(
            AUTH_URL,
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            self.token = response.json()["auth"]["access_token"]
        return response

    def think(self, message, thread_id=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "message": message,
            "thread_id": thread_id
        }
        res = requests.post(f"{self.base_url}/api/v1/ai/think", headers=headers, json=payload)
        return res

@pytest.fixture(scope="module")
def client():
    c = TestClient()
    res = c.authenticate()
    assert res.status_code == 200
    return c

@pytest.mark.asyncio
class TestHallucinationGuard:
    
    def test_identity_anchoring(self, client):
        """Verify the AI correctly identifies as MTF Olympus and rejects external associations."""
        res = client.think("Who are you?")
        assert res.status_code == 200
        data = res.json()["data"]
        response_text = data["response"].lower()
        
        # 1. Identity Check
        assert "mtf olympus" in response_text
        assert "institutional" in response_text
        
        # 2. Rejection of Hallucinations
        assert "microsoft" not in response_text
        assert "olympus corporation" not in response_text
        assert "legend ea" not in response_text

    def test_technical_truth_registry(self, client):
        """Verify the AI knows the correct internal endpoints and architecture."""
        res = client.think("What are your proprietary API endpoints for order placement?")
        assert res.status_code == 200
        data = res.json()["data"]
        response_text = data["response"]
        
        # Should reference endpoints from SYSTEM_PERSONA
        assert "/api/v1/execution/orders" in response_text
        assert "/api/v1/ai/think" in response_text
        assert "Execution Service" in response_text

    def test_search_guard_trigger(self, client):
        """Verify that system-related queries trigger the block_web_search flag."""
        # Query about proprietary internal architecture
        res = client.think("Explain the architecture of the Execution Service.")
        assert res.status_code == 200
        data = res.json()["data"]
        
        # Check Search Guard flag in metadata
        assert data["metadata"].get("block_web_search") == True
        
        # Ensure it didn't find external EA info
        assert "legend ea" not in data["response"].lower()

    def test_open_queries_no_block(self, client):
        """Verify that general market queries do NOT trigger the search guard."""
        res = client.think("What is the current macro sentiment for Gold according to COT data?")
        assert res.status_code == 200
        data = res.json()["data"]
        
        # Should NOT be blocked for general research
        assert data["metadata"].get("block_web_search") == False

    def test_thai_language_protocol(self, client):
        """Verify that Thai input triggers the Thai response protocol."""
        res = client.think("สวัสดีครับ แนะนำตัวหน่อย")
        assert res.status_code == 200
        data = res.json()["data"]
        response_text = data["response"]
        
        # Check for Thai characters (Unicode range \u0E00-\u0E7F)
        import re
        thai_pattern = re.compile(r'[\u0E00-\u0E7F]')
        assert thai_pattern.search(response_text) is not None
        assert "MTF Olympus" in response_text

if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
