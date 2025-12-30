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
import httpx

router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["accounts"]
)

# --- Helpers ---
async def verify_oanda_credentials(account_id: str, api_key: str, is_live: bool = False):
    host = "api-fxtrade.oanda.com" if is_live else "api-fxpractice.oanda.com"
    url = f"https://{host}/v3/accounts/{account_id}/summary"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                return
                
            # Error Handling
            try:
                error_data = response.json()
                error_msg = error_data.get('errorMessage', 'Unknown OANDA error')
            except:
                error_msg = f"HTTP {response.status_code}"

            if response.status_code == 401:
                 raise ValueError(f"OANDA Unauthorized (401): Invalid API Token. Check if token is correct.")
            elif response.status_code == 403:
                 env_str = "LIVE" if is_live else "DEMO"
                 raise ValueError(f"OANDA Forbidden (403): {error_msg}. Check if Account ID '{account_id}' belongs to this token, and if Environment '{env_str}' is correct.")
            else:
                 raise ValueError(f"OANDA Connection Failed ({response.status_code}): {error_msg}")

        except httpx.RequestError as e:
             raise ValueError(f"OANDA Network Error: {str(e)}")

# --- Schemas ---

class BrokerAccountCreate(BaseModel):
    fund_id: Optional[uuid.UUID] = None
    broker_name: str = Field(..., description="OANDA, BINANCE, etc.")
    account_name: str = Field(..., description="User friendly alias")
    account_number: Optional[str] = None
    credentials: Dict[str, Any] = Field(..., description="API keys and secrets")
    supported_symbols: Optional[List[str]] = None
    risk_settings: Optional[Dict[str, Any]] = None
    is_live: bool = False

class BrokerAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    supported_symbols: Optional[List[str]] = None
    risk_settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_live: Optional[bool] = None

class BrokerAccountResponse(BaseModel):
    id: uuid.UUID
    fund_id: uuid.UUID
    broker_name: str
    account_name: str
    account_number: Optional[str] = None
    supported_symbols: Optional[List[str]] = None
    risk_settings: Optional[Dict[str, Any]] = None
    is_active: bool
    is_live: bool
    created_at: Any
    
    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("/", response_model=APIResponse[BrokerAccountResponse], status_code=status.HTTP_201_CREATED)
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
    
    # 1. Check for Duplicate Account Number in this Fund
    if account.account_number:
        existing = db.query(BrokerAccount).filter(
            BrokerAccount.fund_id == target_fund_id,
            BrokerAccount.account_number == account.account_number
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Account number {account.account_number} already exists in this fund."
            )
            
    # 2. Verify Broker Credentials (OANDA Only for now)
    if account.broker_name.upper() == "OANDA":
        api_key = account.credentials.get("api_key", "").strip()
        acc_id = account.credentials.get("account_id", "").strip()
        
        # Update credentials with stripped values
        account.credentials["api_key"] = api_key
        account.credentials["account_id"] = acc_id
        
        if not api_key or not acc_id:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing API Key or Account ID for OANDA")
             
        try:
            # Note: This is a synchronous call in an async function, but verify_oanda_credentials is async
            await verify_oanda_credentials(acc_id, api_key, account.is_live)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # Encrypt credentials
    encrypted_creds = encrypt_data(account.credentials)
    
    new_account = BrokerAccount(
        fund_id=target_fund_id,
        broker_name=account.broker_name.upper(),
        account_name=account.account_name,
        account_number=account.account_number if account.account_number else None,
        credentials_encrypted=encrypted_creds,
        supported_symbols=account.supported_symbols,
        risk_settings=account.risk_settings,
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
    if updates.supported_symbols is not None:
        account.supported_symbols = updates.supported_symbols
    if updates.risk_settings is not None:
        account.risk_settings = updates.risk_settings
        
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
