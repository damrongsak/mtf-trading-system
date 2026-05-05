import pytest
import httpx
import os

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000/api/v1")
USER_NAME = "trader1"
USER_PASSWORD = "password123"

@pytest.fixture
def auth_token():
    resp = httpx.post(f"{GATEWAY_URL}/auth/token", data={"username": USER_NAME, "password": USER_PASSWORD})
    assert resp.status_code == 200
    data = resp.json()
    if "auth" in data:
        return data["auth"]["access_token"]
    return data["access_token"]

def test_ai_briefing_connectivity(auth_token):
    """
    TDD Test: Verify that the AI Market Briefing endpoint is reachable and returns 200.
    This test proves the fix for the 503 error.
    """
    with httpx.Client() as client:
        # Increase timeout as briefing can be slow
        response = client.get(
            f"{GATEWAY_URL}/ai/briefing",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=120.0 
        )
        
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "content" in data["data"]
