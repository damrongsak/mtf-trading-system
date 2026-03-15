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
from app.database import SessionLocal

from app.utils.crypto import encrypt_data, decrypt_data
import httpx
import logging

logger = logging.getLogger(__name__)

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
    data = []
    for s in sources:
        # Convert to dict for safe manipulation
        s_dict = {
            "id": s.id,
            "name": s.name,
            "provider": s.provider,
            "type": s.type,
            "config_json": s.config_json,
            "is_active": s.is_active
        }
        
        config = s.config_json
        if isinstance(config, str):
            try:
                decrypted = decrypt_data(config)
                s_dict["config_json"] = decrypted
            except Exception as e:
                logger.error(f"Failed to decrypt DataSource {s.id}: {e}")
            
        data.append(DataSourceResponse.model_validate(s_dict))
    return success_response(data=data)

@router.get("/{source_id}", response_model=APIResponse[DataSourceResponse])
async def get_data_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific data source."""
    s = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Data Source not found")
    
    s_dict = {
        "id": s.id,
        "name": s.name,
        "provider": s.provider,
        "type": s.type,
        "config_json": s.config_json,
        "is_active": s.is_active
    }
    
    try:
        if isinstance(s_dict["config_json"], str):
            s_dict["config_json"] = decrypt_data(s_dict["config_json"])
    except Exception:
        pass

    return success_response(data=DataSourceResponse.model_validate(s_dict))

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

    # Encrypt config_json before saving
    encrypted_config = encrypt_data(data.config_json)

    new_source = DataSource(
        name=data.name,
        provider=data.provider,
        type=data.type,
        config_json=encrypted_config,
        is_active=data.is_active
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    # Return response with decrypted data
    res_data = DataSourceResponse.model_validate(new_source)
    res_data.config_json = data.config_json
    
    return success_response(
        data=res_data, 
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
        source.config_json = encrypt_data(data.config_json)
        
    if data.is_active is not None:
        source.is_active = data.is_active

    db.commit()
    db.refresh(source)
    
    # Return decrypted for UI
    res_data = DataSourceResponse.model_validate(source)
    try:
        if isinstance(source.config_json, str):
            res_data.config_json = decrypt_data(source.config_json)
    except Exception:
        pass

    return success_response(
        data=res_data, 
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
        # Proxy to Data Pipeline for generic/external discovery
        DATA_PIPELINE_URL = "http://data-pipeline:8000/api/v1/discovery/symbols"
        
        config = source.config_json
        try:
            if isinstance(config, str):
                config = decrypt_data(config)
        except Exception:
            pass

        payload = {
            "provider": source.provider,
            "config": config
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Increased timeout for external calls
                resp = await client.post(DATA_PIPELINE_URL, json=payload, timeout=20.0)
                resp.raise_for_status()
                return success_response(data=resp.json())
            except Exception as e:
                # Start of cleanup for fallback or just return empty list?
                # For discovery, failing is better than silently returning empty to indicate config error.
                raise HTTPException(status_code=502, detail=f"Failed to fetch symbols from Data Pipeline: {str(e)}")




    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
