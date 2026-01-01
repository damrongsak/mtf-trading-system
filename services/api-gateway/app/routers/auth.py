from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user_fund import User
from app.security import verify_password, create_access_token, get_password_hash, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from pydantic import BaseModel, ConfigDict
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
    avatar_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class UserUpdateDto(BaseModel):
    username: str | None = None
    email: str | None = None

class PasswordChangeDto(BaseModel):
    old_password: str
    new_password: str

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
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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

@router.put("/profile", response_model=APIResponse[UserResponse])
async def update_user_profile(
    data: UserUpdateDto,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's profile (username and/or email)
    """
    # Check if username is already taken
    if data.username and data.username != current_user.username:
        existing_user = db.query(User).filter(User.username == data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Check if email is already taken
    if data.email and data.email != current_user.email:
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
    
    # Update user
    if data.username:
        current_user.username = data.username
    if data.email:
        current_user.email = data.email
    
    db.commit()
    db.refresh(current_user)
    
    return success_response(
        data=UserResponse.model_validate(current_user),
        message="Profile updated successfully"
    )

@router.post("/profile/avatar", response_model=APIResponse[UserResponse])
async def upload_avatar(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a profile picture for the current user
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Create upload directory if not exists
    upload_dir = Path("/app/static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename (user_id + uuid + ext)
    file_extension = Path(file.filename).suffix
    filename = f"{current_user.id}_{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / filename
    
    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}"
        )
    finally:
        file.file.close()
        
    # Update user profile
    # URL path to be served
    avatar_url = f"/static/uploads/{filename}"
    
    # Remove old avatar if exists? (Optional enhancement)
    
    current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)
    
    return success_response(
        data=UserResponse.model_validate(current_user),
        message="Avatar uploaded successfully"
    )

@router.put("/password")
async def change_password(
    data: PasswordChangeDto,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change the current user's password
    """
    # Verify old password
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(data.new_password)
    db.commit()
    
    return success_response(
        data=None,
        message="Password changed successfully"
    )
