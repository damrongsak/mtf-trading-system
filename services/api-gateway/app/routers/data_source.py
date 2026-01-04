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
