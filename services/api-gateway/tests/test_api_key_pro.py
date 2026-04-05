import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import ApiKey, User, Fund, UserFund
from app.models.user_fund import UserRole
from app.models.api_key import ApiKeyRole
from app.utils.crypto import encrypt_data, decrypt_data
from app.utils.hmac_utils import hmac_signer
import uuid
import time
from datetime import datetime, timedelta, timezone
import json

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_hmac_headers(api_key: str, secret: str, method: str, path: str, body: str = ""):
    timestamp = str(int(time.time()))
    signature = hmac_signer.generate_signature(
        secret=secret,
        timestamp=timestamp,
        method=method,
        path=path,
        body=body
    )
    return {
        "X-API-KEY": api_key,
        "X-SIGNATURE": signature,
        "X-TIMESTAMP": timestamp
    }

def test_api_key_privilege_capping(db_session):
    """Scenario 1: API Key role is capped by user's fund role during creation."""
    db = db_session
    # 1. Setup User and Fund
    user = db.query(User).filter(User.username == "demo1").first()
    if not user:
        pytest.skip("demo1 user not found")
        
    fund = db.query(Fund).first()
    if not fund:
        # Create a fund if none exists
        fund = Fund(name="Test Fund")
        db.add(fund)
        db.commit()

    # 2. Assign TRADER role to user in this fund (score 2)
    user_fund = db.query(UserFund).filter(UserFund.user_id == user.id, UserFund.fund_id == fund.id).first()
    if not user_fund:
        user_fund = UserFund(user_id=user.id, fund_id=fund.id, role=UserRole.TRADER)
        db.add(user_fund)
    else:
        user_fund.role = UserRole.TRADER
    db.commit()

    # 3. Request API Key with OWNER role (score 4)
    from app.routers.auth import create_access_token
    access_token = create_access_token(data={"sub": user.username})
    
    response = client.post(
        "/api/v1/api-keys",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "Capped Key Test",
            "fund_id": str(fund.id),
            "role": "OWNER" # Higher than user's TRADER role
        }
    )
    
    # 4. Verify Capping
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "TRADER" # Capped!
    
    # Clean up
    key_id = data["id"]
    db.query(ApiKey).filter(ApiKey.id == key_id).delete()
    db.commit()

def test_api_key_fund_isolation(db_session):
    """Scenario 2: Fund-locked API key cannot access other funds."""
    db = db_session
    user = db.query(User).filter(User.username == "demo1").first()
    funds = db.query(Fund).limit(2).all()
    if len(funds) < 2:
        # Create second fund
        f2 = Fund(name="Fund B")
        db.add(f2)
        db.commit()
        funds = db.query(Fund).limit(2).all()
    
    fund_a = funds[0]
    fund_b = funds[1]

    # Create key locked to Fund A
    raw_secret = "secret123"
    api_key_str = "key_fund_a_" + str(uuid.uuid4())[:8]
    key_record = ApiKey(
        user_id=user.id,
        fund_id=fund_a.id,
        name="Locked Key",
        api_key=api_key_str,
        api_secret=encrypt_data({"secret": raw_secret}), # Fix: Use dict for encrypt_data
        role=ApiKeyRole.TRADER,
        is_active=True
    )
    db.add(key_record)
    db.commit()

    # Try to access Fund B via SMC Analysis
    path = "/api/v1/external/analysis/smc"
    body = {
        "symbol": "XAU_USD",
        "timeframe": "H1",
        "fund_id": str(fund_b.id)
    }
    body_str = json.dumps(body, separators=(',', ':')) # No whitespace
    headers = get_hmac_headers(api_key_str, raw_secret, "POST", path, body_str)
    
    response = client.post(path, headers=headers, content=body_str) # Use content instead of json
    
    assert response.status_code == 403
    # Check both detail and message for resilience
    res_data = response.json()
    msg = res_data.get("message") or res_data.get("detail", "")
    assert "restricted to fund" in msg

    # Clean up
    db.delete(key_record)
    db.commit()

def test_api_key_ip_whitelisting(db_session):
    """Scenario 3: IP whitelisting enforcement."""
    db = db_session
    user = db.query(User).filter(User.username == "demo1").first()
    
    # Create key with whitelist
    raw_secret = "secret123"
    api_key_str = "key_ip_" + str(uuid.uuid4())[:8]
    key_record = ApiKey(
        user_id=user.id,
        name="IP Key",
        api_key=api_key_str,
        api_secret=encrypt_data({"secret": raw_secret}),
        allowed_ips=["1.1.1.1"], # Only this IP allowed
        is_active=True
    )
    db.add(key_record)
    db.commit()

    path = "/api/v1/external/market/snapshot/XAU_USD"
    headers = get_hmac_headers(api_key_str, raw_secret, "GET", path)
    
    # TestClient uses 127.0.0.1 by default
    response = client.get(path, headers=headers)
    
    assert response.status_code == 403
    res_data = response.json()
    msg = res_data.get("message") or res_data.get("detail", "")
    assert "Client IP not in whitelist" in msg

    # Clean up
    db.delete(key_record)
    db.commit()

def test_api_key_expiration(db_session):
    """Scenario 4: Expired API key."""
    db = db_session
    user = db.query(User).filter(User.username == "demo1").first()
    
    # Create expired key
    raw_secret = "secret123"
    api_key_str = "key_expired_" + str(uuid.uuid4())[:8]
    key_record = ApiKey(
        user_id=user.id,
        name="Expired Key",
        api_key=api_key_str,
        api_secret=encrypt_data({"secret": raw_secret}),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        is_active=True
    )
    db.add(key_record)
    db.commit()

    path = "/api/v1/external/market/snapshot/XAU_USD"
    headers = get_hmac_headers(api_key_str, raw_secret, "GET", path)
    
    response = client.get(path, headers=headers)
    
    assert response.status_code == 401
    res_data = response.json()
    msg = res_data.get("message") or res_data.get("detail", "")
    assert "expired" in msg

    # Clean up
    db.delete(key_record)
    db.commit()

def test_api_key_dynamic_role_demotion(db_session):
    """Scenario 5: Effective role is demoted if user's fund role decreases."""
    db = db_session
    user = db.query(User).filter(User.username == "demo1").first()
    fund = db.query(Fund).first()
    
    # 1. Key created when user was MANAGER (score 3)
    user_fund = db.query(UserFund).filter(UserFund.user_id == user.id, UserFund.fund_id == fund.id).first()
    if not user_fund:
        user_fund = UserFund(user_id=user.id, fund_id=fund.id, role=UserRole.MANAGER)
        db.add(user_fund)
    else:
        user_fund.role = UserRole.MANAGER
    db.commit()

    raw_secret = "secret123"
    api_key_str = "key_demote_" + str(uuid.uuid4())[:8]
    key_record = ApiKey(
        user_id=user.id,
        fund_id=fund.id,
        name="Demotion Key",
        api_key=api_key_str,
        api_secret=encrypt_data({"secret": raw_secret}),
        role=ApiKeyRole.MANAGER, # Key has MANAGER role
        is_active=True
    )
    db.add(key_record)
    db.commit()

    # 2. User demoted to VIEWER (score 1)
    user_fund.role = UserRole.VIEWER
    db.commit()

    # 3. Access SMC analysis (requires TRADER+)
    path = "/api/v1/external/analysis/smc"
    body = {
        "symbol": "XAU_USD",
        "timeframe": "H1",
        "fund_id": str(fund.id)
    }
    body_str = json.dumps(body, separators=(',', ':'))
    headers = get_hmac_headers(api_key_str, raw_secret, "POST", path, body_str)
    
    response = client.post(path, headers=headers, content=body_str)
    
    # Should fail with 403 because effective role is now VIEWER (capped by current user role)
    assert response.status_code == 403
    res_data = response.json()
    msg = res_data.get("message") or res_data.get("detail", "")
    assert "Insufficient privileges" in msg

    # Clean up
    db.delete(key_record)
    db.commit()

