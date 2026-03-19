import pytest
import httpx
import os
import asyncio
import time
from typing import Dict, Any

# Environment variables for configuration
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")
USERNAME = os.getenv("E2E_USERNAME", "demo1")
PASSWORD = os.getenv("E2E_PASSWORD", "password123")

# Note: event_loop fixture is removed (handled by pytest-asyncio loop_scope)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def api_client():
    """Provide an HTTPX AsyncClient for the API."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client

@pytest.fixture(scope="session")
async def auth_headers(api_client):
    """Fixture to obtain and provide auth headers."""
    url = "/api/v1/auth/token"
    # Note: data should be a dict or a string. requests uses data=, httpx uses data= too.
    # api-gateway uses form data for OAuth2PasswordRequestForm
    response = await api_client.post(url, data={"username": USERNAME, "password": PASSWORD})
    
    assert response.status_code == 200, f"Auth failed ({response.status_code}): {response.text}"
    data = response.json()
    token = data["auth"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
async def broker_account(api_client, auth_headers):
    """Fixture to get an active broker account for testing."""
    url = "/api/v1/execution/accounts"
    response = await api_client.get(url, headers=auth_headers)
    assert response.status_code == 200, f"Failed to get accounts: {response.text}"
    
    accounts = response.json()["data"]
    assert accounts, "No active broker accounts found for testing"
    return accounts[0]

class AsyncPolling:
    """Helper for robust async polling of state changes."""
    @staticmethod
    async def wait_until(func, timeout=60, interval=2, message="State change timeout"):
        start_time = time.time()
        while time.time() - start_time < timeout:
            result, success = await func()
            if success:
                return result
            await asyncio.sleep(interval)
        raise TimeoutError(message)

@pytest.fixture
def poller():
    return AsyncPolling()
