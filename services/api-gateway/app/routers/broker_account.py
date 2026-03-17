from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user_fund import Fund, UserFund, UserRole
from app.models.user_preferences import UserPreferences
from app.security import get_current_user
from app.dependencies.rbac import RequireRole, get_fund_id_from_account
from app.utils.crypto import encrypt_data, decrypt_data
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.response import APIResponse
from app.utils.response import success_response
from typing import List, Optional, Dict, Any
import uuid
import httpx
import hmac
import hashlib
import time
from app.models.market import MarketCategory, MarketSymbol
from app.models.broker_account import BrokerAccount
from app.models.data_source import DataSource
from fastapi import Request
import os
import logging

from app.schemas.generated import (
    BrokerAccount as GeneratedBrokerAccount,
    BrokerAccountCreate as GeneratedBrokerAccountCreate,
    BrokerAccountUpdate as GeneratedBrokerAccountUpdate
)

logger = logging.getLogger(__name__)

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

def categorize_binance_instrument(symbol_info: Dict[str, Any]) -> str:
    """Categorize Binance instrument (Crypto)."""
    # Simply return Crypto for now as we are likely trading Spot or Futures
    # Use logic if needed (e.g. if 'contractType' in info -> Futures)
    return "Crypto"

async def verify_binance_credentials(api_key: str, secret_key: str, is_live: bool = False):
    """Verify Binance credentials by fetching account info."""
    # Base URL
    base_url = "https://api.binance.com" if is_live else "https://testnet.binance.vision" 
    # Note: Testnet URL might be different or require different keys. 
    # For simplicity, assuming User provides standard keys. 
    # If is_live=False, we might default to testnet.binance.vision/api
    
    endpoint = "/api/v3/account"
    
    timestamp = int(time.time() * 1000)
    params = f"timestamp={timestamp}"
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    url = f"{base_url}{endpoint}?{params}&signature={signature}"
    
    headers = {
        "X-MBX-APIKEY": api_key
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                return
                
            try:
                err = response.json()
                msg = err.get('msg', 'Unknown Error')
            except:
                msg = response.text
                
            if response.status_code == 401:
                 raise ValueError(f"Binance Unauthorized: Check API Key/Secret. ({msg})")
            else:
                 raise ValueError(f"Binance Connection Failed ({response.status_code}): {msg}")

        except httpx.RequestError as e:
             raise ValueError(f"Binance Network Error: {str(e)}")

async def fetch_binance_instruments(api_key: str, secret_key: str, is_live: bool = False) -> List[Dict[str, Any]]:
    """Fetch all trading symbols from Binance."""
    # We don't strictly need auth for exchangeInfo but it's good practice to use the same base_url
    base_url = "https://api.binance.com" if is_live else "https://testnet.binance.vision"
    url = f"{base_url}/api/v3/exchangeInfo"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            if response.status_code != 200:
                 raise ValueError(f"Failed to fetch symbols: HTTP {response.status_code}")
                 
            data = response.json()
            symbols = data.get("symbols", [])
            # Return full objects to helper
            return symbols
            
        except Exception as e:
             raise ValueError(f"Binance Symbol Fetch Error: {str(e)}")

async def verify_ctrader_credentials(credentials: Dict[str, Any], is_live: bool = False):
    """Verify cTrader credentials via Data Pipeline discovery."""
    client_id = credentials.get("client_id", "").strip()
    client_secret = credentials.get("client_secret", "").strip()
    token = credentials.get("token", "").strip()
    account_id = credentials.get("account_id", "").strip()
    
    if not all([client_id, client_secret, token, account_id]):
        missing = [k for k, v in {"client_id": client_id, "client_secret": client_secret, "token": token, "account_id": account_id}.items() if not v]
        raise ValueError(f"Missing required cTrader credentials: {', '.join(missing)}")
        
    discovery_payload = {
        "provider": "CTRADER",
        "config": {
            "host": "live.ctraderapi.com" if is_live else "demo.ctraderapi.com",
            "port": 5035,
            "client_id": client_id,
            "client_secret": client_secret,
            "account_id": account_id,
            "token": token
        }
    }
    
    DATA_SERVICE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/discovery/symbols",
                json=discovery_payload,
                timeout=20.0
            )
            
            if resp.status_code != 200:
                try:
                    err_data = resp.json()
                    detail = err_data.get("detail", resp.text)
                except:
                    detail = resp.text
                raise ValueError(f"cTrader Verification Failed: {detail}")
                
            return # Success
            
        except httpx.RequestError as e:
            raise ValueError(f"Data Pipeline Connection Error: {str(e)}")

# --- Schemas ---

class BrokerAccountResponse(GeneratedBrokerAccount):
    credentials: Optional[Dict[str, Any]] = None
    created_at: Optional[Any] = None
    
    model_config = ConfigDict(from_attributes=True)

# --- Endpoints ---

@router.post("/", response_model=APIResponse[BrokerAccountResponse], status_code=status.HTTP_201_CREATED)
async def create_account(
    request: Request,
    account: GeneratedBrokerAccountCreate,
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

    # Verify User has access to this Fund with OWNER or MANAGER role
    rbac = RequireRole([UserRole.OWNER, UserRole.MANAGER])
    user_fund = await rbac(request, fund_id=target_fund_id, db=db, current_user=current_user)
    
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

    elif account.broker_name.upper() == "BINANCE":
        api_key = account.credentials.get("api_key", "").strip()
        secret_key = account.credentials.get("secret_key", "").strip()
        
        # Update credentials
        account.credentials["api_key"] = api_key
        account.credentials["secret_key"] = secret_key
        
        if not api_key or not secret_key:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing API Key or Secret Key for Binance")
             
        try:
            await verify_binance_credentials(api_key, secret_key, account.is_live)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            
    elif account.broker_name.upper() in ["CTRADER", "ICMARKETS", "ICMARKETSSC"]:
        try:
            # Sync account_id to credentials if passed in account_number
            if account.account_number and "account_id" not in account.credentials:
                account.credentials["account_id"] = account.account_number
            
            await verify_ctrader_credentials(account.credentials, account.is_live)
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
        is_active=True,
        # [NEW] Phase 28 Fields
        data_source_id=account.data_source_id,
        leverage=account.leverage,
        currency=account.currency,
        balance_snapshot=account.balance_snapshot
    )
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    
    resp_data = BrokerAccountResponse.model_validate(new_account)
    resp_data.credentials = account.credentials
    
    return success_response(
        data=resp_data,
        message="Broker account added successfully"
    )

@router.get("/", response_model=APIResponse[List[BrokerAccountResponse]])
async def list_accounts(
    fund_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all broker accounts for funds user has access to."""
    query = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
        UserFund.user_id == current_user.id
    )
    
    if fund_id:
        query = query.filter(BrokerAccount.fund_id == fund_id)
        
    accounts = query.all()
    
    # RBAC: Mask credentials for VIEWER roles. 
    user_fund_map = {uf.fund_id: uf.role for uf in db.query(UserFund).filter(UserFund.user_id == current_user.id).all()}
    
    resp_list = []
    for a in accounts:
        item = BrokerAccountResponse.model_validate(a)
        role = user_fund_map.get(a.fund_id)
        
        # Security: Only decrypt credentials for OWNER and MANAGER
        if a.credentials_encrypted and role in [UserRole.OWNER, UserRole.MANAGER]:
            try:
                item.credentials = decrypt_data(a.credentials_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt credentials for account {a.id}: {e}")
        else:
            # Mask or Omit
            item.credentials = {"masked": "******** (Insufficient Permissions)"} if a.credentials_encrypted else None
            
        resp_list.append(item)
    
    return success_response(
        data=resp_list
    )

@router.put("/{account_id}", response_model=APIResponse[BrokerAccountResponse])
async def update_account(
    account_id: uuid.UUID,
    updates: GeneratedBrokerAccountUpdate,
    fund_id: uuid.UUID = Depends(get_fund_id_from_account),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    user_fund: UserFund = Depends(RequireRole([UserRole.OWNER, UserRole.MANAGER]))
):
    """Update a broker account."""
    account = db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
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
    
    # [NEW] Phase 28 Fields
    if updates.data_source_id is not None:
        account.data_source_id = updates.data_source_id
    if updates.leverage is not None:
        account.leverage = updates.leverage
    if updates.currency is not None:
        account.currency = updates.currency
    if updates.balance_snapshot is not None:
        account.balance_snapshot = updates.balance_snapshot
        
    db.commit()
    db.refresh(account)
    
    resp_data = BrokerAccountResponse.model_validate(account)
    if account.credentials_encrypted:
        try:
            resp_data.credentials = decrypt_data(account.credentials_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for account {account.id}: {e}")
            
    return success_response(
        data=resp_data,
        message="Broker account updated successfully"
    )

@router.delete("/{account_id}")
async def delete_account(
    account_id: uuid.UUID,
    fund_id: uuid.UUID = Depends(get_fund_id_from_account),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    user_fund: UserFund = Depends(RequireRole([UserRole.OWNER]))
):
    """Delete a broker account."""
    account = db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
         
    db.delete(account)
    db.commit()
    
    return success_response(data=None, message="Broker account deleted")


@router.post("/{account_id}/fetch-symbols", response_model=APIResponse[List[str]])
async def fetch_account_symbols(
    account_id: uuid.UUID,
    fund_id: uuid.UUID = Depends(get_fund_id_from_account),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    user_fund: UserFund = Depends(RequireRole([UserRole.OWNER, UserRole.MANAGER, UserRole.TRADER]))
):
    """Fetch tradable symbols. Prioritizes local DB cache to prevent rate limits."""
    account = db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
         
    if account.broker_name not in ["OANDA", "BINANCE", "CTRADER", "ICMARKETS", "ICMARKETSSC"]:
        return success_response(data=[], message="Fetching symbols not supported for this broker yet")

    # Proxy to Data Pipeline for cTrader based brokers
    if account.broker_name in ["CTRADER", "ICMARKETS", "ICMARKETSSC"]:
        try:
            creds = decrypt_data(account.credentials_encrypted)
            
            # Prepare config for Data Pipeline Discovery
            # ensure keys match what AsyncCTraderClient expects in data-pipeline
            discovery_payload = {
                "provider": "CTRADER",
                "config": {
                    "host": "live.ctraderapi.com" if account.is_live else "demo.ctraderapi.com",
                    "port": 5035,
                    "client_id": creds.get("client_id"),
                    "client_secret": creds.get("client_secret"),
                    "account_id": creds.get("account_id"),
                    "token": creds.get("token")
                }
            }
            
            DATA_SERVICE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{DATA_SERVICE_URL}/api/v1/discovery/symbols",
                    json=discovery_payload,
                    timeout=20.0
                )
                
                if resp.status_code != 200:
                    raise ValueError(f"Data Pipeline Error: {resp.text}")
                    
                raw_symbols = resp.json()
                
                # Sync Logic (Similar to other brokers)
                # 1. Ensure DataSource
                data_source = db.query(DataSource).filter(DataSource.name == "CTRADER").first()
                if not data_source:
                     data_source = DataSource(name="CTRADER", type="api", config_json={})
                     db.add(data_source)
                     db.flush()
                     
                # 2. Ensure Categories
                # cTrader symbols (Forex, Metals) vs Crypto. Harder to categorize by name alone.
                # We'll default to 'Forex' or 'Other' for now or try simple heuristic
                categories = {c.name: c for c in db.query(MarketCategory).all()}
                
                # 3. Bulk Save
                synced_count = 0
                symbol_list = []
                
                existing_syms = {s.symbol: s for s in db.query(MarketSymbol).filter(MarketSymbol.data_source_id == data_source.id).all()}
                
                for name in raw_symbols:
                    symbol_list.append(name)
                    
                    # Simple Categorization
                    cat_name = "Other"
                    if "/" in name or len(name) == 6 or "USD" in name or "EUR" in name:
                         cat_name = "Forex"
                    if "XAU" in name or "XAG" in name:
                         cat_name = "Metals"
                    if "BTC" in name or "ETH" in name:
                         cat_name = "Crypto"
                         
                    cat_obj = categories.get(cat_name) 
                    if not cat_obj:
                        # Create if missing or map to Other
                        if "Other" in categories:
                            cat_obj = categories["Other"]
                        else:
                            # Fallback if DB empty
                            continue 
                            
                    if name not in existing_syms:
                        new_sym = MarketSymbol(
                            category_id=cat_obj.id,
                            data_source_id=data_source.id,
                            symbol=name,
                            display_name=name,
                            order_index=999
                        )
                        db.add(new_sym)
                        synced_count += 1
                    else:
                        # Reactivate if inactive?
                        pass
                
                db.commit()
                return success_response(data=symbol_list, message=f"Fetched {len(symbol_list)} symbols (New: {synced_count})")

        except Exception as e:
            logger.error(f"cTrader fetch failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # 1. Try fetching from Local DB - DISABLED for explicit fetch
    # This logic was flawed (hardcoded OANDA) and prevented updates.
    # explicit 'fetch-symbols' action should always hit the broker.
    # If we want to return local symbols, we should use a different endpoint or param.

    # 2. Cold Start: Fetch from Broker & Sync to DB
    try:
        creds = decrypt_data(account.credentials_encrypted)
        
        if account.broker_name == "BINANCE":
            api_key = creds.get("api_key")
            secret_key = creds.get("secret_key")
            
            if not api_key or not secret_key:
                 raise HTTPException(status_code=400, detail="Missing API Key or Secret Key")
                 
            # Fetch raw
            raw_symbols = await fetch_binance_instruments(api_key, secret_key, account.is_live)
            
            # Sync Logic
            # 1. Ensure DataSource
            data_source = db.query(DataSource).filter(DataSource.name == "BINANCE").first()
            if not data_source:
                 data_source = DataSource(name="BINANCE", type="api", config_json={})
                 db.add(data_source)
                 db.flush()
                 
            # 2. Ensure Categories
            cat_name = "Crypto"
            category = db.query(MarketCategory).filter(MarketCategory.name == cat_name).first()
            if not category:
                category = MarketCategory(name=cat_name, order_index=2)
                db.add(category)
                db.flush()
                
            # 3. Bulk Save
            symbol_list = []
            synced_count = 0
            
            # Fetch existing to avoid duplicates
            existing_syms = {s.symbol for s in db.query(MarketSymbol).filter(MarketSymbol.data_source_id == data_source.id).all()}
            
            for info in raw_symbols:
                name = info['symbol']
                quote_asset = info.get('quoteAsset')
                
                # Check status
                if info.get('status') != 'TRADING':
                    continue

                # Filter: Only USDT pairs for now to prevent UI flooding (~300 vs 1600)
                if quote_asset != "USDT":
                     continue
                
                symbol_list.append(name)
                
                if name not in existing_syms:
                    new_sym = MarketSymbol(
                        category_id=category.id,
                        data_source_id=data_source.id,
                        symbol=name,
                        display_name=f"{info.get('baseAsset')}/{info.get('quoteAsset')}",
                        order_index=999
                    )
                    db.add(new_sym)
                    existing_syms.add(name)
                    synced_count += 1
            
            db.commit()
            return success_response(data=symbol_list, message=f"Fetched {len(symbol_list)} symbols (New: {synced_count})")

        elif account.broker_name == "OANDA":
            api_key = creds.get("api_key")
            acc_id = creds.get("account_id")
            
            if not api_key or not acc_id:
                 raise HTTPException(status_code=400, detail="Missing credentials")
                 
            # Fetch raw names first (lightweight) - SKIPPED
            # We use full fetch below to get details
            
            # Sync Logic
            # Check for OANDA DataSource
            data_source = db.query(DataSource).filter(DataSource.name == "OANDA").first()
            if not data_source:
                # OANDA DataSource is missing and auto-creation is disabled. 
                # User must manually ensure it is active if needed (but we are moving away from it).
                raise HTTPException(status_code=400, detail="OANDA data source not found or deactivated.")

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
            synced_count = 0
            symbol_list = []

            host = "api-fxtrade.oanda.com" if account.is_live else "api-fxpractice.oanda.com"
            url = f"https://{host}/v3/accounts/{acc_id}/instruments"
            
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
                                 order_index=999,
                                 details=inst  # Store full Oanda details
                             )
                             db.add(new_sym)
                             synced_count += 1
                         else:
                             # Update details if existing
                             if existing_sym.details != inst:
                                 existing_sym.details = inst
                                 synced_count += 1
                     
                     db.commit()

            return success_response(data=symbol_list, message=f"Fetched and cached {len(symbol_list)} symbols")
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in fetch_account_symbols")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{account_id}/refresh-token")
async def refresh_account_token(
    account_id: uuid.UUID,
    fund_id: uuid.UUID = Depends(get_fund_id_from_account),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    user_fund: UserFund = Depends(RequireRole([UserRole.OWNER, UserRole.MANAGER, UserRole.TRADER]))
):
    """
    Refresh Access Token using stored Refresh Token (cTrader).
    """
    account = db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    if account.broker_name not in ["CTRADER", "ICMARKETS", "ICMARKETSSC"]:
        raise HTTPException(status_code=400, detail="Only cTrader supports manual token refresh")
        
    try:
        creds = decrypt_data(account.credentials_encrypted)
        refresh_token = creds.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(status_code=400, detail="No refresh token found")
            
        payload = {
            "provider": "CTRADER",
            "config": {
                 "host": "live.ctraderapi.com" if account.is_live else "demo.ctraderapi.com",
                 "port": 5035,
                 "client_id": creds.get("client_id"),
                 "client_secret": creds.get("client_secret"),
                 "refresh_token": refresh_token
            }
        }
        
        # Ensure httpx is imported? It is used throughout.
        # Ensure os is imported.
        DATA_SERVICE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/discovery/refresh-token",
                json=payload,
                timeout=20.0
            )
            
            if resp.status_code != 200:
                raise ValueError(f"Data Pipeline Error: {resp.text}")
                
            data = resp.json()
            new_access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 2592000) # Default 30 days if missing
            
            # Update DB
            creds["token"] = new_access_token
            creds["refresh_token"] = new_refresh_token
            # Store absolute expiry time (now + seconds)
            creds["expires_at"] = int(time.time()) + int(expires_in)
            
            account.credentials_encrypted = encrypt_data(creds)
            db.commit()
            
            return success_response(message="Token refreshed successfully")
            
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
