import pytest
from unittest.mock import MagicMock, patch
from datetime import timedelta
from app.security import verify_password, get_password_hash, create_access_token, get_current_user
from fastapi import HTTPException
from jose import jwt
import app.security as security_module

def test_password_hashing():
    pw = "secret"
    hashed = get_password_hash(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("wrong", hashed)

def test_token_creation():
    data = {"sub": "testuser"}
    token = create_access_token(data, expires_delta=timedelta(minutes=10))
    decoded = jwt.decode(token, security_module.SECRET_KEY, algorithms=[security_module.ALGORITHM])
    assert decoded["sub"] == "testuser"
    assert "exp" in decoded

def test_get_current_user_valid():
    token = create_access_token({"sub": "dantest"})
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.username = "dantest"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    user = get_current_user(token=token, db=mock_db)
    assert user.username == "dantest"

def test_get_current_user_invalid_token():
    mock_db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        get_current_user(token="invalid", db=mock_db)
    assert exc.value.status_code == 401

def test_get_current_user_no_sub():
    # Token without sub?
    # jwt.encode allow arbitrary dict.
    token = jwt.encode({}, security_module.SECRET_KEY, algorithm=security_module.ALGORITHM)
    mock_db = MagicMock()
    with pytest.raises(HTTPException):
        get_current_user(token=token, db=mock_db)

def test_get_current_user_not_found():
    token = create_access_token({"sub": "ghost"})
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    with pytest.raises(HTTPException):
        get_current_user(token=token, db=mock_db)
