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
