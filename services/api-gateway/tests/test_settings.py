from unittest.mock import MagicMock, patch
from app.models.user_preferences import UserPreferences, StrategyType
from app.schemas.response import ResponseStatus
import uuid

def test_get_preferences_existing(client, mock_db_session, mock_current_user):
    """Test GET /api/v1/settings/preferences returns existing preferences"""
    from app.security import get_current_user
    
    pref_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    mock_prefs = MagicMock(spec=UserPreferences)
    mock_prefs.id = pref_id
    mock_prefs.user_id = mock_current_user.id
    mock_prefs.default_fund_id = fund_id
    mock_prefs.strategy_type = StrategyType.MTF_SMC_BASIC
    mock_prefs.asset_classes = ["FX"]
    mock_prefs.max_risk_per_trade = 10.0
    mock_prefs.default_lot_size = 0.01
    mock_prefs.max_drawdown_threshold = None
    mock_prefs.max_portfolio_beta = 0.35
    mock_prefs.gross_exposure_limit = 100.0
    mock_prefs.net_exposure_limit = 15.0
    mock_prefs.position_limit_single = 3.0
    mock_prefs.position_limit_sector = 10.0
    mock_prefs.preferred_timeframes = ["4H", "1H", "15m"]
    mock_prefs.default_symbol = "XAU/USD"
    mock_prefs.session_preferences = ["LONDON", "NY"]
    mock_prefs.supported_symbols = []
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prefs
    
    # Mock the UserPreferencesResponse model_validate
    mock_response_data = {
        "id": str(pref_id),
        "user_id": str(mock_current_user.id),
        "default_fund_id": str(fund_id),
        "strategy_type": "MTF_SMC_BASIC",
        "asset_classes": ["FX"],
        "max_risk_per_trade": 10.0,
        "default_lot_size": 0.01,
        "max_drawdown_threshold": None,
        "max_portfolio_beta": 0.35,
        "gross_exposure_limit": 100.0,
        "net_exposure_limit": 15.0,
        "position_limit_single": 3.0,
        "position_limit_sector": 10.0,
        "preferred_timeframes": ["4H", "1H", "15m"],
        "default_symbol": "XAU/USD",
        "session_preferences": ["LONDON", "NY"],
        "supported_symbols": []
    }
    
    with patch('app.routers.settings.UserPreferencesResponse') as MockResponse:
        mock_instance = MagicMock()
        mock_instance.model_dump.return_value = mock_response_data
        MockResponse.model_validate.return_value = mock_instance
        
        app = client.app
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        
        response = client.get("/api/v1/settings/preferences")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        assert data["data"]["strategy_type"] == "MTF_SMC_BASIC"
        assert data["data"]["default_symbol"] == "XAU/USD"
        assert data["data"]["max_risk_per_trade"] == 10.0
        
        app.dependency_overrides.pop(get_current_user)


def test_get_preferences_creates_default(client, mock_db_session, mock_current_user):
    """Test GET /api/v1/settings/preferences creates default preferences if none exist"""
    from app.security import get_current_user
    
    # Mock DB returning None (no preferences)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    pref_id = uuid.uuid4()
    mock_response_data = {
        "id": str(pref_id),
        "user_id": str(mock_current_user.id),
        "default_fund_id": None,
        "strategy_type": "MTF_SMC_BASIC",
        "asset_classes": ["FX"],
        "max_risk_per_trade": 10.0,
        "default_lot_size": 0.01,
        "max_drawdown_threshold": None,
        "max_portfolio_beta": None,
        "gross_exposure_limit": None,
        "net_exposure_limit": None,
        "position_limit_single": None,
        "position_limit_sector": None,
        "preferred_timeframes": ["4H", "1H", "15m"],
        "default_symbol": "XAU/USD",
        "session_preferences": None,
        "supported_symbols": None
    }
    
    with patch('app.routers.settings.UserPreferencesResponse') as MockResponse:
        mock_instance = MagicMock()
        mock_instance.model_dump.return_value = mock_response_data
        MockResponse.model_validate.return_value = mock_instance
        
        app = client.app
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        
        response = client.get("/api/v1/settings/preferences")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        assert data["data"]["strategy_type"] == "MTF_SMC_BASIC"
        assert data["data"]["default_symbol"] == "XAU/USD"
        
        # Verify DB operations
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        
        app.dependency_overrides.pop(get_current_user)


def test_update_preferences_success(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/settings/preferences updates preferences"""
    from app.security import get_current_user
    
    pref_id = uuid.uuid4()
    mock_prefs = MagicMock(spec=UserPreferences)
    mock_prefs.id = pref_id
    mock_prefs.user_id = mock_current_user.id
    mock_prefs.strategy_type = StrategyType.MTF_SMC_BASIC
    mock_prefs.default_symbol = "XAU/USD"
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prefs
    
    mock_response_data = {
        "id": str(pref_id),
        "user_id": str(mock_current_user.id),
        "default_fund_id": None,
        "strategy_type": "MTF_SMC_BASIC",
        "asset_classes": ["FX"],
        "max_risk_per_trade": 5.0,
        "default_lot_size": 0.01,
        "max_drawdown_threshold": None,
        "max_portfolio_beta": None,
        "gross_exposure_limit": None,
        "net_exposure_limit": None,
        "position_limit_single": None,
        "position_limit_sector": None,
        "preferred_timeframes": ["4H", "1H"],
        "default_symbol": "XAU/USD",
        "session_preferences": None,
        "supported_symbols": None
    }
    
    with patch('app.routers.settings.UserPreferencesResponse') as MockResponse:
        mock_instance = MagicMock()
        mock_instance.model_dump.return_value = mock_response_data
        MockResponse.model_validate.return_value = mock_instance
        
        app = client.app
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        
        update_data = {
            "max_risk_per_trade": 5.0,
            "preferred_timeframes": ["4H", "1H"]
        }
        
        response = client.put("/api/v1/settings/preferences", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        
        # Verify DB operations
        assert mock_db_session.commit.called
        assert mock_db_session.refresh.called
        
        app.dependency_overrides.pop(get_current_user)


def test_update_preferences_validation_xauusd(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/settings/preferences validates XAU/USD for basic strategy"""
    from app.security import get_current_user
    
    mock_prefs = MagicMock(spec=UserPreferences)
    mock_prefs.id = uuid.uuid4()
    mock_prefs.user_id = mock_current_user.id
    mock_prefs.strategy_type = StrategyType.MTF_SMC_BASIC
    mock_prefs.default_symbol = "XAU/USD"
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prefs
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    # Try to update to EUR/USD with basic strategy
    update_data = {
        "default_symbol": "EUR/USD"
    }
    
    response = client.put("/api/v1/settings/preferences", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR
    assert "XAU/USD" in data["errors"][0]["message"]
    
    app.dependency_overrides.pop(get_current_user)


def test_update_preferences_advanced_strategy(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/settings/preferences allows any symbol for advanced strategies"""
    from app.security import get_current_user
    
    pref_id = uuid.uuid4()
    mock_prefs = MagicMock(spec=UserPreferences)
    mock_prefs.id = pref_id
    mock_prefs.user_id = mock_current_user.id
    mock_prefs.strategy_type = StrategyType.LONG_SHORT_EQUITY
    mock_prefs.default_symbol = "SPX"
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prefs
    
    mock_response_data = {
        "id": str(pref_id),
        "user_id": str(mock_current_user.id),
        "default_fund_id": None,
        "strategy_type": "LONG_SHORT_EQUITY",
        "asset_classes": ["EQUITY", "FX"],
        "max_risk_per_trade": 10.0,
        "default_lot_size": 0.01,
        "max_drawdown_threshold": None,
        "max_portfolio_beta": 0.35,
        "gross_exposure_limit": 200.0,
        "net_exposure_limit": 15.0,
        "position_limit_single": 3.0,
        "position_limit_sector": 10.0,
        "preferred_timeframes": ["4H", "1H"],
        "default_symbol": "EUR/USD",
        "session_preferences": ["NY"],
        "supported_symbols": ["SPX", "QQQ", "EUR/USD"]
    }
    
    with patch('app.routers.settings.UserPreferencesResponse') as MockResponse:
        mock_instance = MagicMock()
        mock_instance.model_dump.return_value = mock_response_data
        MockResponse.model_validate.return_value = mock_instance
        
        app = client.app
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        
        update_data = {
            "strategy_type": "LONG_SHORT_EQUITY",
            "default_symbol": "EUR/USD",
            "gross_exposure_limit": 200.0
        }
        
        response = client.put("/api/v1/settings/preferences", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        
        app.dependency_overrides.pop(get_current_user)


def test_update_preferences_creates_if_not_exists(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/settings/preferences creates preferences if none exist"""
    from app.security import get_current_user
    
    # Mock DB returning None
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    pref_id = uuid.uuid4()
    mock_response_data = {
        "id": str(pref_id),
        "user_id": str(mock_current_user.id),
        "default_fund_id": None,
        "strategy_type": "MTF_SMC_BASIC",
        "asset_classes": ["FX"],
        "max_risk_per_trade": 5.0,
        "default_lot_size": 0.01,
        "max_drawdown_threshold": None,
        "max_portfolio_beta": None,
        "gross_exposure_limit": None,
        "net_exposure_limit": None,
        "position_limit_single": None,
        "position_limit_sector": None,
        "preferred_timeframes": ["4H", "1H", "15m"],
        "default_symbol": "XAU/USD",
        "session_preferences": None,
        "supported_symbols": None
    }
    
    with patch('app.routers.settings.UserPreferencesResponse') as MockResponse:
        mock_instance = MagicMock()
        mock_instance.model_dump.return_value = mock_response_data
        MockResponse.model_validate.return_value = mock_instance
        
        app = client.app
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        
        update_data = {
            "max_risk_per_trade": 5.0
        }
        
        response = client.put("/api/v1/settings/preferences", json=update_data)
        
        assert response.status_code == 200
        
        # Verify DB operations
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        
        app.dependency_overrides.pop(get_current_user)

