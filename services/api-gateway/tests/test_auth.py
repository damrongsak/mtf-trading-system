from unittest.mock import MagicMock, patch
from app.models.user_fund import User
from app.schemas.response import ResponseStatus, ErrorCode
import uuid

def test_login_success(client, mock_db_session):
    # Setup mock user
    user_id = uuid.uuid4()
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.password_hash = "hashed_password"
    mock_user.avatar_url = None
    
    # Mock DB query
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Mock security functions
    with patch("app.routers.auth.verify_password", return_value=True), \
         patch("app.routers.auth.create_access_token", return_value="fake_token"):
        
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "testuser", "password": "password"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        assert data["auth"]["access_token"] == "fake_token"
        assert data["data"]["username"] == "testuser"

def test_login_invalid_credentials(client, mock_db_session):
    # Mock DB query returning None (user not found)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "wronguser", "password": "password"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR
    assert data["errors"][0]["code"] == ErrorCode.UNAUTHORIZED

def test_register_success(client, mock_db_session):
    # Mock DB query returning None (user doesn't exist)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    # Mock security functions
    with patch("app.routers.auth.get_password_hash", return_value="hashed_password"), \
         patch("app.routers.auth.create_access_token", return_value="fake_token"):
        
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "email": "new@example.com", "password": "password"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        assert data["auth"]["access_token"] == "fake_token"
        assert data["data"]["username"] == "newuser"
        
        # Verify DB add/commit called
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

def test_register_duplicate_user(client, mock_db_session):
    # Mock DB query returning existing user
    mock_db_session.query.return_value.filter.return_value.first.return_value = MagicMock()
    
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "existinguser", "email": "existing@example.com", "password": "password"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR

def test_get_profile(client, mock_current_user):
    from app.security import get_current_user
    
    # Override get_current_user dependency
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.get("/api/v1/auth/profile")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["username"] == mock_current_user.username
    
    app.dependency_overrides.pop(get_current_user)

def test_update_profile_success(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/auth/profile updates user profile"""
    from app.security import get_current_user
    
    # Mock DB query returning None (username not taken)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.put(
        "/api/v1/auth/profile",
        json={"username": "newusername", "email": "newemail@example.com"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["message"] == "Profile updated successfully"
    
    # Verify DB commit called
    assert mock_db_session.commit.called
    assert mock_db_session.refresh.called
    
    app.dependency_overrides.pop(get_current_user)

def test_update_profile_duplicate_username(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/auth/profile rejects duplicate username"""
    from app.security import get_current_user
    
    # Create a different user with the target username
    existing_user = MagicMock(spec=User)
    existing_user.username = "existinguser"
    existing_user.id = uuid.uuid4()  # Different ID
    existing_user.avatar_url = None
    
    # Mock DB query returning existing user
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing_user
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.put(
        "/api/v1/auth/profile",
        json={"username": "existinguser"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR
    assert "already taken" in data["errors"][0]["message"].lower()
    
    app.dependency_overrides.pop(get_current_user)

def test_update_profile_duplicate_email(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/auth/profile rejects duplicate email"""
    from app.security import get_current_user
    
    existing_user = MagicMock(spec=User)
    existing_user.email = "existing@example.com"
    existing_user.id = uuid.uuid4()
    existing_user.avatar_url = None
    
    # Setup query mocks - first call for username returns None, second for email returns existing user
    username_query = MagicMock()
    username_query.filter.return_value.first.return_value = None
    
    email_query = MagicMock()
    email_query.filter.return_value.first.return_value = existing_user
    
    mock_db_session.query.side_effect = [username_query, email_query]
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.put(
        "/api/v1/auth/profile",
        json={"username": "newusername", "email": "existing@example.com"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR
    assert "already in use" in data["errors"][0]["message"].lower()
    
    app.dependency_overrides.pop(get_current_user)

def test_change_password_success(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/auth/password changes password successfully"""
    from app.security import get_current_user
    
    with patch("app.routers.auth.verify_password", return_value=True), \
         patch("app.routers.auth.get_password_hash", return_value="new_hashed_password"):
        
        app = client.app
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        
        response = client.put(
            "/api/v1/auth/password",
            json={"old_password": "oldpass", "new_password": "newpass"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        assert data["message"] == "Password changed successfully"
        
        # Verify DB commit called
        assert mock_db_session.commit.called
        
        app.dependency_overrides.pop(get_current_user)

def test_change_password_wrong_old_password(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/auth/password rejects incorrect old password"""
    from app.security import get_current_user
    
    with patch("app.routers.auth.verify_password", return_value=False):
        app = client.app
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        
        response = client.put(
            "/api/v1/auth/password",
            json={"old_password": "wrongpass", "new_password": "newpass"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == ResponseStatus.ERROR
        assert "incorrect" in data["errors"][0]["message"].lower()
        
        app.dependency_overrides.pop(get_current_user)
