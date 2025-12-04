from unittest.mock import MagicMock, patch
from app.models.user_preferences import UserPreferences, StrategyType
from app.schemas.response import ResponseStatus
import uuid

def test_get_preferences_existing(client, mock_db_session, mock_current_user):
    """Test GET /api/v1/settings/preferences returns existing preferences"""
    from app.security import get_current_user
    
    pref_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    # Use real UserPreferences instance instead of MagicMock
    prefs = UserPreferences(
        id=pref_id,
        user_id=mock_current_user.id,
        default_fund_id=fund_id,
        strategy_type=StrategyType.MTF_SMC_BASIC,
        asset_classes=["FX"],
        max_risk_per_trade=10.0,
        default_lot_size=0.01,
        max_drawdown_threshold=None,
        max_portfolio_beta=0.35,
        gross_exposure_limit=100.0,
        net_exposure_limit=15.0,
        position_limit_single=3.0,
        position_limit_sector=10.0,
        preferred_timeframes=["4H", "1H", "15m"],
        default_symbol="XAU/USD",
        session_preferences=["LONDON", "NY"],
        supported_symbols=[]
    )
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = prefs
    
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
    
    # After creation, the refresh will populate the instance
    def mock_refresh(instance):
        instance.id = uuid.uuid4()
        # Set defaults that would be set by DB
        if getattr(instance, 'strategy_type', None) is None:
            instance.strategy_type = StrategyType.MTF_SMC_BASIC
        if getattr(instance, 'default_lot_size', None) is None:
            instance.default_lot_size = 0.01
        if getattr(instance, 'default_symbol', None) is None:
            instance.default_symbol = "XAU/USD"
        if getattr(instance, 'max_risk_per_trade', None) is None:
            instance.max_risk_per_trade = 10.0
    
    mock_db_session.refresh.side_effect = mock_refresh
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    # First query returns None (no preferences exist)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
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
    
    # Use real UserPreferences instance
    prefs = UserPreferences(
       id=pref_id,
        user_id=mock_current_user.id,
        strategy_type=StrategyType.MTF_SMC_BASIC,
        default_symbol="XAU/USD",
        asset_classes=["FX"],
        max_risk_per_trade=10.0,
        default_lot_size=0.01,
        max_drawdown_threshold=None,
        max_portfolio_beta=None,
        gross_exposure_limit=None,
        net_exposure_limit=None,
        position_limit_single=None,
        position_limit_sector=None,
        preferred_timeframes=["4H", "1H", "15m"],
        session_preferences=None,
        supported_symbols=None,
        default_fund_id=None
    )
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = prefs
    
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
    
    # Use real UserPreferences instance
    prefs = UserPreferences(
        id=uuid.uuid4(),
        user_id=mock_current_user.id,
        strategy_type=StrategyType.MTF_SMC_BASIC,
        default_symbol="XAU/USD",
        asset_classes=["FX"],
        max_risk_per_trade=10.0,
        default_lot_size=0.01,
        max_drawdown_threshold=None,
        max_portfolio_beta=None,
        gross_exposure_limit=None,
        net_exposure_limit=None,
        position_limit_single=None,
        position_limit_sector=None,
        preferred_timeframes=["4H", "1H", "15m"],
        session_preferences=None,
        supported_symbols=None,
        default_fund_id=None
    )
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = prefs
    
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
    
    # Use real UserPreferences instance
    prefs = UserPreferences(
        id=pref_id,
        user_id=mock_current_user.id,
        strategy_type=StrategyType.LONG_SHORT_EQUITY,
        default_symbol="SPX",
        asset_classes=["EQUITY", "FX"],
        max_risk_per_trade=10.0,
        default_lot_size=0.01,
        max_drawdown_threshold=None,
        max_portfolio_beta=0.35,
        gross_exposure_limit=200.0,
        net_exposure_limit=15.0,
        position_limit_single=3.0,
        position_limit_sector=10.0,
        preferred_timeframes=["4H", "1H"],
        session_preferences=["NY"],
        supported_symbols=["SPX", "QQQ", "EUR/USD"],
        default_fund_id=None
    )
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = prefs
    
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
    
    # After creation, the refresh will populate the instance
    def mock_refresh(instance):
        instance.id = uuid.uuid4()
        # Set defaults that would be set by DB
        if getattr(instance, 'strategy_type', None) is None:
            instance.strategy_type = StrategyType.MTF_SMC_BASIC
        if getattr(instance, 'default_lot_size', None) is None:
            instance.default_lot_size = 0.01
        if getattr(instance, 'default_symbol', None) is None:
            instance.default_symbol = "XAU/USD"
        if getattr(instance, 'max_risk_per_trade', None) is None:
            instance.max_risk_per_trade = 10.0
    
    mock_db_session.refresh.side_effect = mock_refresh
    
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

