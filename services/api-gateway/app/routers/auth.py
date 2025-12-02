from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user_fund import User
from app.security import verify_password, create_access_token, get_password_hash, get_current_user
from pydantic import BaseModel
from datetime import timedelta
from app.schemas.response import APIResponse, AuthTokens, ErrorCode
from app.utils.response import success_response, create_auth_tokens, error_response
import uuid

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    
    class Config:
        from_attributes = True

@router.post("/token", response_model=APIResponse[UserResponse])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Allow login with either username or email
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    auth_tokens = create_auth_tokens(
        user_id=str(user.id),
        access_token=access_token,
        expires_in=int(access_token_expires.total_seconds())
    )
    
    return success_response(
        data=UserResponse.model_validate(user),
        message="Login successful",
        auth=auth_tokens
    )

@router.post("/register", response_model=APIResponse[UserResponse])
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.username})
    auth_tokens = create_auth_tokens(
        user_id=str(new_user.id),
        access_token=access_token
    )
    
    return success_response(
        data=UserResponse.model_validate(new_user),
        message="User registered successfully",
        auth=auth_tokens
    )

@router.get("/profile", response_model=APIResponse[UserResponse])
async def get_current_user_profile(current_user = Depends(get_current_user)):
    """
    Get the current authenticated user's profile
    """
    return success_response(data=UserResponse.model_validate(current_user))
