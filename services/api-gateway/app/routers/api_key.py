from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import secrets
import string
import uuid
from app.database import get_db
from app.security import get_current_user
from app.models import User, ApiKey
from app.models.api_key import ApiKeyRole
from app.models.user_fund import UserFund, UserRole as UserFundRole
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate
from app.utils.crypto import encrypt_data
from app.utils.response import success_response

router = APIRouter(prefix="/api-keys", tags=["API Key Management"])

def generate_secure_string(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_hierarchical_role_value(role: str) -> int:
    # OWNER(4) > MANAGER(3) > TRADER(2) > VIEWER(1)
    values = {"OWNER": 4, "MANAGER": 3, "TRADER": 2, "VIEWER": 1}
    return values.get(role, 0)

@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all API keys for the current user."""
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
    return keys

@router.post("", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    req: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new Professional-Grade API Key and Secret."""
    
    # 1. RBAC Validation (Privilege Capping)
    role_to_save = ApiKeyRole(req.role)
    
    if req.fund_id:
        # Check user's role in this fund
        user_fund = db.query(UserFund).filter(
            UserFund.user_id == current_user.id,
            UserFund.fund_id == req.fund_id
        ).first()
        
        if not user_fund:
            raise HTTPException(status_code=403, detail="You do not have access to this fund.")
        
        user_fund_score = get_hierarchical_role_value(user_fund.role.value)
        req_role_score = get_hierarchical_role_value(req.role)
        
        # Silent Capping: Use the lower of the two scores
        if req_role_score > user_fund_score:
            role_to_save = ApiKeyRole(user_fund.role.value)
        else:
            role_to_save = ApiKeyRole(req.role)

    # 2. Generate Key & Secret
    new_key = f"ak_live_{generate_secure_string(24)}"
    new_secret = generate_secure_string(32)

    # 3. Encrypt Secret for storage
    encrypted_secret = encrypt_data({"secret": new_secret})

    # 4. Save to DB
    api_key_obj = ApiKey(
        user_id=current_user.id,
        fund_id=req.fund_id,
        name=req.name,
        api_key=new_key,
        api_secret=encrypted_secret,
        role=role_to_save,
        scopes=req.scopes,
        allowed_ips=req.allowed_ips,
        expires_at=req.expires_at,
        rate_limit_rpm=req.rate_limit_rpm,
        is_active=True
    )
    
    db.add(api_key_obj)
    db.commit()
    db.refresh(api_key_obj)

    # 5. Return response (include plain secret ONCE)
    response = ApiKeyResponse.model_validate(api_key_obj)
    response.api_secret = new_secret
    return response


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: uuid.UUID,
    req: ApiKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update API Key metadata."""
    key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    
    if req.name is not None: key.name = req.name
    if req.is_active is not None: key.is_active = req.is_active
    if req.allowed_ips is not None: key.allowed_ips = req.allowed_ips
    if req.expires_at is not None: key.expires_at = req.expires_at
    if req.rate_limit_rpm is not None: key.rate_limit_rpm = req.rate_limit_rpm
    
    db.commit()
    db.refresh(key)
    return key

@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permanently delete/revoke an API Key."""
    key = db.query(ApiKey).filter(
        ApiKey.id == key_id, 
        ApiKey.user_id == current_user.id
    ).first()

    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")

    db.delete(key)
    db.commit()
    return success_response(message="API Key revoked successfully")
