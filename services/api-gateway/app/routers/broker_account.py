from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.broker_account import BrokerAccount
from app.models.user_fund import Fund, UserFund
from app.models.user_preferences import UserPreferences
from app.security import get_current_user
from app.utils.crypto import encrypt_data, decrypt_data
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.response import APIResponse
from app.utils.response import success_response
from typing import List, Optional, Dict, Any
import uuid
import httpx
from app.models.market import MarketCategory, MarketSymbol
from app.models.data_source import DataSource

router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["accounts"]
)

# --- Helpers ---

def categorize_oanda_instrument(instrument: Dict[str, Any]) -> str:
    """Categorize OANDA instrument based on tags/name."""
    name = instrument.get("name", "")
    type_ = instrument.get("type", "")
    
    if type_ == "CURRENCY":
        return "Forex"
    elif type_ == "CFD":
        if "XAU" in name or "XAG" in name:
            return "Metals"
        if "BTC" in name or "ETH" in name or "LTC" in name:
            return "Crypto"
        if "US30" in name or "SPX" in name or "NAS" in name or "DE30" in name:
            return "Indices"
        return "CFD"
    elif type_ == "METAL":
        return "Metals"
        
    return "Other"

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

async def fetch_oanda_instruments(account_id: str, api_key: str, is_live: bool = False) -> List[str]:
    host = "api-fxtrade.oanda.com" if is_live else "api-fxpractice.oanda.com"
    url = f"https://{host}/v3/accounts/{account_id}/instruments"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            
            if response.status_code != 200:
                # Reuse error logic or simplify
                raise ValueError(f"Failed to fetch symbols: HTTP {response.status_code}")
                
            data = response.json()
            instruments = data.get("instruments", [])
            return [inst["name"] for inst in instruments]
            
        except Exception as e:
             raise ValueError(f"OANDA Symbol Fetch Error: {str(e)}")

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
    
    model_config = ConfigDict(from_attributes=True)

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


@router.post("/{account_id}/fetch-symbols", response_model=APIResponse[List[str]])
async def fetch_account_symbols(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Fetch tradable symbols. Prioritizes local DB cache to prevent rate limits."""
    account = db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    user_fund = db.query(UserFund).filter(
        UserFund.user_id == current_user.id,
        UserFund.fund_id == account.fund_id
    ).first()
    
    if not user_fund:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    if account.broker_name != "OANDA":
        return success_response(data=[], message="Fetching symbols not supported for this broker yet")

    # 1. Try fetching from Local DB
    data_source = db.query(DataSource).filter(DataSource.name == "OANDA").first()
    if data_source:
        local_symbols = db.query(MarketSymbol).filter(MarketSymbol.data_source_id == data_source.id).all()
        if local_symbols:
             return success_response(
                 data=[s.symbol for s in local_symbols], 
                 message=f"Returned {len(local_symbols)} cached symbols"
             )

    # 2. Cold Start: Fetch from Broker & Sync to DB
    try:
        creds = decrypt_data(account.credentials_encrypted)
        api_key = creds.get("api_key")
        acc_id = creds.get("account_id")
        
        if not api_key or not acc_id:
             raise HTTPException(status_code=400, detail="Missing credentials")
             
        # Fetch raw instruments
        instruments = await fetch_oanda_instruments(acc_id, api_key, account.is_live)
        
        # Sync Logic (Ported from script)
        if not data_source:
            # Create DataSource if missing
             data_source = DataSource(name="OANDA", type="api", config_json={})
             db.add(data_source)
             db.flush()

        # Ensure categories exist
        cat_names = ["Forex", "Metals", "Crypto", "Indices", "CFD", "Other"]
        categories = {c.name: c for c in db.query(MarketCategory).all()}
        
        for idx, name in enumerate(cat_names):
            if name not in categories:
                new_cat = MarketCategory(name=name, order_index=idx)
                db.add(new_cat)
                categories[name] = new_cat
        db.flush() 

        # Bulk Create/Update Symbols
        # Note: We return raw names immediately, but sync to DB for next time
        synced_count = 0
        symbol_list = []

        host = "api-fxtrade.oanda.com" if account.is_live else "api-fxpractice.oanda.com"
        url = f"https://{host}/v3/accounts/{acc_id}/instruments"
        
        # We need full instrument details for categorization, so we re-fetch fully
        # Reuse helper but modify it to return full objects? 
        # Alternatively, fetch_oanda_instruments returned names only. 
        # Let's modify the helper OR just fetch manually here since this is a rare "cold start".
        
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient() as client:
             resp_full = await client.get(url, headers=headers)
             if resp_full.status_code == 200:
                 full_instruments = resp_full.json().get("instruments", [])
                 
                 for inst in full_instruments:
                     name = inst['name']
                     symbol_list.append(name)
                     display_name = inst.get('displayName', name)
                     
                     cat_name = categorize_oanda_instrument(inst)
                     cat_obj = categories.get(cat_name, categories["Other"])
                     
                     # Check existence
                     existing_sym = db.query(MarketSymbol).filter(
                         MarketSymbol.symbol == name, 
                         MarketSymbol.data_source_id == data_source.id
                     ).first()
                     
                     if not existing_sym:
                         new_sym = MarketSymbol(
                             category_id=cat_obj.id,
                             data_source_id=data_source.id,
                             symbol=name,
                             display_name=display_name,
                             order_index=999
                         )
                         db.add(new_sym)
                         synced_count += 1
                 
                 db.commit()

        return success_response(data=symbol_list, message=f"Fetched and cached {len(symbol_list)} symbols")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
