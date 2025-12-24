from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.broker_account import BrokerAccount
from app.models.user_fund import Fund, UserFund
from app.models.user_preferences import UserPreferences
from app.security import get_current_user
from app.utils.crypto import encrypt_data, decrypt_data
from pydantic import BaseModel, Field
from app.schemas.response import APIResponse
from app.utils.response import success_response
from typing import List, Optional, Dict, Any
import uuid

router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["accounts"]
)

# --- Schemas ---

class BrokerAccountCreate(BaseModel):
    fund_id: Optional[uuid.UUID] = None
    broker_name: str = Field(..., description="OANDA, BINANCE, etc.")
    account_name: str = Field(..., description="User friendly alias")
    account_number: Optional[str] = None
    credentials: Dict[str, Any] = Field(..., description="API keys and secrets")
    is_live: bool = False

class BrokerAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_live: Optional[bool] = None

class BrokerAccountResponse(BaseModel):
    id: uuid.UUID
    fund_id: uuid.UUID
    broker_name: str
    account_name: str
    account_number: Optional[str] = None
    is_active: bool
    is_live: bool
    created_at: Any
    
    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("/", response_model=APIResponse[BrokerAccountResponse])
async def create_account(
    account: BrokerAccountCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add a new broker account to a fund."""
    
    target_fund_id = account.fund_id
    
    if not target_fund_id:
        # Try identifying default fund
        prefs = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
        if prefs and prefs.default_fund_id:
            target_fund_id = prefs.default_fund_id
        else:
            # Fallback to first available fund
            first_access = db.query(UserFund).filter(UserFund.user_id == current_user.id).first()
            if first_access:
                target_fund_id = first_access.fund_id
            else:
                 raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="No fund found. Please create a fund first."
                )

    # Verify User has access to this Fund
    user_fund = db.query(UserFund).filter(
        UserFund.user_id == current_user.id,
        UserFund.fund_id == target_fund_id
    ).first()
    
    if not user_fund:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to manage this fund"
        )
    
    # Encrypt credentials
    encrypted_creds = encrypt_data(account.credentials)
    
    new_account = BrokerAccount(
        fund_id=target_fund_id,
        broker_name=account.broker_name.upper(),
        account_name=account.account_name,
        account_number=account.account_number if account.account_number else None,
        credentials_encrypted=encrypted_creds,
        is_live=account.is_live,
        is_active=True
    )
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    return success_response(
        data=BrokerAccountResponse.model_validate(new_account),
        message="Broker account added successfully"
    )

@router.get("/", response_model=APIResponse[List[BrokerAccountResponse]])
async def list_accounts(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all broker accounts for funds user has access to."""
    accounts = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
        UserFund.user_id == current_user.id
    ).all()
    
    return success_response(
        data=[BrokerAccountResponse.model_validate(a) for a in accounts]
    )

@router.put("/{account_id}", response_model=APIResponse[BrokerAccountResponse])
async def update_account(
    account_id: uuid.UUID,
    updates: BrokerAccountUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a broker account."""
    account = db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check permission logic
    user_fund = db.query(UserFund).filter(
        UserFund.user_id == current_user.id,
        UserFund.fund_id == account.fund_id
    ).first()
    
    if not user_fund:
         raise HTTPException(status_code=403, detail="Not authorized")
        
    if updates.account_name is not None:
        account.account_name = updates.account_name
    if updates.account_number is not None:
        account.account_number = updates.account_number
    if updates.is_active is not None:
        account.is_active = updates.is_active
    if updates.is_live is not None:
        account.is_live = updates.is_live
    if updates.credentials is not None:
        account.credentials_encrypted = encrypt_data(updates.credentials)
        
    db.commit()
    db.refresh(account)
    
    return success_response(
        data=BrokerAccountResponse.model_validate(account),
        message="Broker account updated successfully"
    )

@router.delete("/{account_id}")
async def delete_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a broker account."""
    account = db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    # Check permission logic
    user_fund = db.query(UserFund).filter(
        UserFund.user_id == current_user.id,
        UserFund.fund_id == account.fund_id
    ).first()
    
    if not user_fund:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    db.delete(account)
    db.commit()
    
    return success_response(data=None, message="Broker account deleted")
