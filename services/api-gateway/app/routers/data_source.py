from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app.models.data_source import DataSource
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate, DataSourceResponse
from app.schemas.response import APIResponse
from app.utils.response import success_response
from app.security import get_current_user
from fastapi import BackgroundTasks
from app.routers.broker_account import fetch_binance_instruments
from app.database import SessionLocal

router = APIRouter(
    prefix="/data-sources",
    tags=["data-sources"],
    responses={404: {"description": "Not found"}},
)

@router.get("", response_model=APIResponse[List[DataSourceResponse]])
async def get_data_sources(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all data sources."""
    sources = db.query(DataSource).all()
    # Convert ORM to Pydantic explicitly to avoid serialization errors
    data = [DataSourceResponse.model_validate(s) for s in sources]
    return success_response(data=data)

@router.get("/{source_id}", response_model=APIResponse[DataSourceResponse])
async def get_data_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific data source."""
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Data Source not found")
    return success_response(data=DataSourceResponse.model_validate(source))

@router.post("", response_model=APIResponse[DataSourceResponse])
async def create_data_source(
    data: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new data source."""
    # Check uniqueness
    existing = db.query(DataSource).filter(DataSource.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Data Source '{data.name}' already exists")

    new_source = DataSource(
        name=data.name,
        provider=data.provider,
        type=data.type,
        config_json=data.config_json,
        is_active=data.is_active
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    return success_response(
        data=DataSourceResponse.model_validate(new_source), 
        message="Data Source created successfully"
    )

@router.put("/{source_id}", response_model=APIResponse[DataSourceResponse])
async def update_data_source(
    source_id: uuid.UUID,
    data: DataSourceUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a data source."""
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Data Source not found")
        
    if data.name:
         # Check unique if renaming
         existing = db.query(DataSource).filter(DataSource.name == data.name, DataSource.id != source_id).first()
         if existing:
            raise HTTPException(status_code=400, detail=f"Data Source '{data.name}' already exists")
         source.name = data.name
         
    if data.type:
        source.type = data.type
    
    if data.config_json is not None:
        source.config_json = data.config_json
        
    if data.is_active is not None:
        source.is_active = data.is_active

    db.commit()
    db.refresh(source)
    return success_response(
        data=DataSourceResponse.model_validate(source), 
        message="Data Source updated successfully"
    )

@router.delete("/{source_id}")
async def delete_data_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a data source."""
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Data Source not found")
        
    # TODO: Check for usage in MarketSymbol before deleting to prevent orphans?
    # For now, we allow deletion as admin knows best.
    
    db.delete(source)
    db.commit()
    return success_response(data=None, message="Data Source deleted successfully")

import httpx

@router.post("/{source_id}/backfill")
async def trigger_backfill(
    source_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Trigger a background backfill task via Data Pipeline Service.
    Payload: {symbol: str, timeframe: str, count: int}
    """
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Data Source not found")

    symbol = payload.get("symbol")
    timeframe = payload.get("timeframe")
    
    if not symbol or not timeframe:
        raise HTTPException(status_code=400, detail="Symbol and Timeframe are required")

    # Forward to Data Pipeline
    DATA_PIPELINE_URL = "http://data-pipeline:8000/api/v1/backfill"
    
    # Map payload to BackfillRequest schema
    request_data = {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": payload.get("count", 2500)
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(DATA_PIPELINE_URL, json=request_data)
            resp.raise_for_status()
            data_pipeline_resp = resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to contact Data Pipeline: {str(e)}")

    return success_response(
        data={"status": "queued", "job_id": data_pipeline_resp.get("job_id")},
        message=f"Backfill started for {symbol} (via Pipeline)"
    )

@router.get("/{source_id}/symbols")
async def get_source_symbols(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Fetch available symbols from the data source provider."""
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Data Source not found")
        
    try:
        if source.provider == "OANDA":
             # Use the service we created to fetch symbols?
             # Or just raw client. The service doesn't have list_symbols yet.
             # Let's instantiate service and use client from it?
             # Or add list_symbols to service.
             
             # Quick fix: direct client usage or expand service.
             # Expanding service is cleaner.
             # For now, let's just return a static list if service expansion is too much, 
             # OR try to reuse what we have.
             # Let's do a quick inline fetch using the config
            config = source.config_json
            from oandapyV20 import API
            import oandapyV20.endpoints.accounts as accounts
            
            hostname = config.get("hostname", "api-fxtrade.oanda.com")
            token = config.get("token")
            env = "practice" if "practice" in hostname else "live"
            
            client = API(access_token=token, environment=env)
            account_id = config.get("account_id")
            
            # Use AccountInstruments endpoint
            r = accounts.AccountInstruments(accountID=account_id)
            client.request(r)
            
            instruments = r.response.get("instruments", [])
            # Format: {symbol: "EUR_USD", ...}
            # Return list of strings
            symbols = [i['name'] for i in instruments]
            return success_response(data=symbols)

        elif source.provider == "BINANCE":
             # Reuse helper from broker_account
             # Check credentials
             api_key = source.config_json.get("api_key")
             secret_key = source.config_json.get("secret_key")
             # is_live logic?
             is_live = not source.config_json.get("testnet", False)
             
             if not api_key:
                  return success_response(data=[])

             raw_symbols = await fetch_binance_instruments(api_key, secret_key, is_live)
             symbols = [s['symbol'] for s in raw_symbols if s['status'] == 'TRADING']
             return success_response(data=symbols)
             
        else:
            return success_response(data=[])

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
