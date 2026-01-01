import pytest
from datetime import timedelta
from app.security import verify_password, get_password_hash, create_access_token
from jose import jwt
import os

def test_password_hashing():
    pwd = "secretpassword"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed)
    assert not verify_password("wrong", hashed)

def test_create_access_token():
    data = {"sub": "testuser"}
    token = create_access_token(data)
    decoded = jwt.decode(token, os.getenv("SECRET_KEY", "supersecretkey"), algorithms=["HS256"])
    assert decoded["sub"] == "testuser"
    assert "exp" in decoded

def test_create_access_token_with_expiry():
    data = {"sub": "testuser"}
    expires = timedelta(minutes=5)
    token = create_access_token(data, expires_delta=expires)
    decoded = jwt.decode(token, os.getenv("SECRET_KEY", "supersecretkey"), algorithms=["HS256"])
    assert decoded["sub"] == "testuser"
