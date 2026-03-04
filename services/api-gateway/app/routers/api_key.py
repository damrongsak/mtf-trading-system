from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import secrets
import string
from app.database import get_db
from app.security import get_current_user
from app.models import User, ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse
from app.utils.crypto import encrypt_data
from app.utils.response import success_response

router = APIRouter(prefix="/api-keys", tags=["API Key Management"])

def generate_secure_string(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all API keys for the current user."""
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
    # Mask secrets (already done by schema default None)
    return keys

@router.post("", response_model=ApiKeyResponse)
async def create_api_key(
    req: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new API Key and Secret."""
    # 1. Generate Key & Secret
    # api_key format: ak_live_...
    new_key = f"ak_live_{generate_secure_string(24)}"
    new_secret = generate_secure_string(32)

    # 2. Encrypt Secret for storage (crypto.py expects a dict)
    encrypted_secret = encrypt_data({"secret": new_secret})

    # 3. Save to DB
    api_key_obj = ApiKey(
        user_id=current_user.id,
        name=req.name,
        api_key=new_key,
        api_secret=encrypted_secret,
        is_active=True
    )
    
    db.add(api_key_obj)
    db.commit()
    db.refresh(api_key_obj)

    # 4. Return response (include plain secret ONCE)
    response = ApiKeyResponse.from_orm(api_key_obj)
    response.api_secret = new_secret
    return response

@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
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
