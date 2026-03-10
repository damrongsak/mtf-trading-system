import sys
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
sys.modules["app.services.gemini_client"] = MagicMock()
sys.modules["app.services.rag_service"] = MagicMock()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import app

client = TestClient(app)

def test_list_agents():
    response = client.get("/api/v1/ai/agents")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 3
    
    agent_ids = [a["id"] for a in data["data"]]
    assert "market_observer" in agent_ids
    assert "strategy_advisor" in agent_ids

def test_get_agent_details():
    response = client.get("/api/v1/ai/agents/market_observer")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["id"] == "market_observer"
    assert "capabilities" in data["data"]

def test_get_agent_not_found():
    response = client.get("/api/v1/ai/agents/non_existent_agent")
    assert response.status_code == 404
