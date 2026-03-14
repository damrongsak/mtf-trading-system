import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.routers.broker_account import verify_ctrader_credentials
from app.models.broker_account import BrokerAccount
from app.models.user_fund import UserFund, UserRole
from app.models.user_preferences import UserPreferences
from app.security import get_current_user
import uuid
import httpx

@pytest.mark.asyncio
async def test_verify_ctrader_credentials_success():
    credentials = {
        "client_id": "test_id",
        "client_secret": "test_secret",
        "token": "test_token",
        "account_id": "12345"
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        
        await verify_ctrader_credentials(credentials, is_live=False)
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["config"]["account_id"] == "12345"
        assert "demo.ctraderapi.com" in kwargs["json"]["config"]["host"]

@pytest.mark.asyncio
async def test_verify_ctrader_credentials_missing_fields():
    credentials = {
        "client_id": "test_id",
        "client_secret": "test_secret"
    }
    
    with pytest.raises(ValueError, match="Missing required cTrader credentials"):
        await verify_ctrader_credentials(credentials)

@pytest.mark.asyncio
async def test_create_account_icmarkets_success(client, mock_db_session, mock_current_user):
    # Setup
    fund_id = uuid.uuid4()
    mock_user_fund = UserFund(user_id=mock_current_user.id, fund_id=fund_id, role=UserRole.OWNER)
    
    def query_side_effect(model):
        query_mock = MagicMock()
        filter_mock = MagicMock()
        if model == UserPreferences:
             filter_mock.first.return_value = UserPreferences(user_id=mock_current_user.id, default_fund_id=fund_id)
        elif model == UserFund:
             filter_mock.first.return_value = mock_user_fund
        elif model == BrokerAccount:
             filter_mock.first.return_value = None
        else:
             filter_mock.first.return_value = None
        query_mock.filter.return_value = filter_mock
        return query_mock

    mock_db_session.query.side_effect = query_side_effect
    
    with patch("app.routers.broker_account.verify_ctrader_credentials", new_callable=AsyncMock) as mock_verify:
        payload = {
            "fund_id": str(fund_id),
            "broker_name": "ICMARKETS",
            "account_name": "My IC Account",
            "account_number": "12345",
            "credentials": {
                "client_id": "cid",
                "client_secret": "cs",
                "token": "tok"
            }
        }
        
        from app.main import app
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        
        response = client.post("/api/v1/accounts/", json=payload)
        
        assert response.status_code == 201
        assert mock_verify.called
        # Check if account_id was synced from account_number
        args = mock_verify.call_args[0]
        assert args[0]["account_id"] == "12345"
        
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_account_ctrader_fail_verification(client, mock_db_session, mock_current_user):
    # Setup
    fund_id = uuid.uuid4()
    mock_user_fund = UserFund(user_id=mock_current_user.id, fund_id=fund_id, role=UserRole.OWNER)
    
    # Configure mock_db_session.query to return proper mocks for each call
    def query_side_effect(model):
        query_mock = MagicMock()
        filter_mock = MagicMock()
        if model == UserPreferences:
             filter_mock.first.return_value = UserPreferences(user_id=mock_current_user.id, default_fund_id=fund_id)
        elif model == UserFund:
             filter_mock.first.return_value = mock_user_fund
        elif model == BrokerAccount:
             filter_mock.first.return_value = None
        else:
             filter_mock.first.return_value = None
        query_mock.filter.return_value = filter_mock
        return query_mock

    mock_db_session.query.side_effect = query_side_effect
    
    with patch("app.routers.broker_account.verify_ctrader_credentials", side_effect=ValueError("Invalid Token")):
        payload = {
            "fund_id": str(fund_id),
            "broker_name": "CTRADER",
            "account_name": "Fail Account",
            "account_number": "12345",
            "credentials": {
                "client_id": "cid",
                "client_secret": "cs",
                "token": "tok",
                "account_id": "12345"
            }
        }
        
        from app.main import app
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        
        response = client.post("/api/v1/accounts/", json=payload)
        
        assert response.status_code == 400
        assert "Invalid Token" in response.json()["message"]
        
        app.dependency_overrides.clear()
