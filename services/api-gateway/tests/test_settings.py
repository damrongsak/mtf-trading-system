from unittest.mock import MagicMock, patch
from app.models.user_preferences import UserPreferences
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
        preferred_timeframes=["4H", "1H", "15m"],
        default_symbol="XAU/USD",
        session_preferences=["LONDON", "NY"]
    )
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = prefs
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.get("/api/v1/settings/preferences")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["default_symbol"] == "XAU/USD"
    
    app.dependency_overrides.pop(get_current_user)


def test_get_preferences_creates_default(client, mock_db_session, mock_current_user):
    """Test GET /api/v1/settings/preferences creates default preferences if none exist"""
    from app.security import get_current_user
    
    # After creation, the refresh will populate the instance
    def mock_refresh(instance):
        instance.id = uuid.uuid4()
        # Set defaults that would be set by DB
        if getattr(instance, 'default_symbol', None) is None:
            instance.default_symbol = "XAU/USD"
    
    mock_db_session.refresh.side_effect = mock_refresh
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    # First query returns None (no preferences exist)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/api/v1/settings/preferences")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
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
        default_symbol="XAU/USD",
        preferred_timeframes=["4H", "1H", "15m"],
        session_preferences=None,
        default_fund_id=None
    )
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = prefs
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    update_data = {
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


def test_update_preferences_creates_if_not_exists(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/settings/preferences creates preferences if none exist"""
    from app.security import get_current_user
    
    # Mock DB returning None
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    # After creation, the refresh will populate the instance
    def mock_refresh(instance):
        instance.id = uuid.uuid4()
        # Set defaults that would be set by DB
        if getattr(instance, 'default_symbol', None) is None:
            instance.default_symbol = "XAU/USD"
    
    mock_db_session.refresh.side_effect = mock_refresh
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    update_data = {
        "default_symbol": "EUR/USD"
    }
    
    response = client.put("/api/v1/settings/preferences", json=update_data)
    
    assert response.status_code == 200
    
    # Verify DB operations
    assert mock_db_session.add.called
    assert mock_db_session.commit.called
    
    app.dependency_overrides.pop(get_current_user)

