
import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app

client = TestClient(app)

def test_list_plugins():
    response = client.get("/internal/plugins")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_inspect_hooks():
    with patch("app.routers.plugins.strategy_engine") as mock_engine:
        mock_engine.hook_manager.actions = {"on_signal": []}
        mock_engine.hook_manager.filters = {"filter_gamma": []}
        
        response = client.get("/internal/plugins/hooks")
        assert response.status_code == 200
        assert "actions" in response.json()
        assert "filters" in response.json()

def test_notify_dispatched():
    with patch("app.routers.plugins.strategy_engine") as mock_engine:
        payload = {"message": "Test Notification", "category": "info"}
        response = client.post("/internal/plugins/notify", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "dispatched"
        mock_engine.notify.assert_called_once()
