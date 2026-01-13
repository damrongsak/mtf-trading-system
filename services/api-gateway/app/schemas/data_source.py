from pydantic import BaseModel, Field, ConfigDict, Json
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from enum import Enum

class DataSourceType(str, Enum):
    API = "api"
    CSV = "csv"
    DB = "db"
    WEBSOCKET = "websocket"

class DataSourceProvider(str, Enum):
    OANDA = "OANDA"
    BINANCE = "BINANCE"

class DataSourceBase(BaseModel):
    name: str = Field(..., description="User-defined alias")
    provider: DataSourceProvider = Field(..., description="Provider Implementation")
    type: DataSourceType = Field(..., description="Type of source")
    config_json: Dict[str, Any] = Field(default_factory=dict, description="Configuration (API keys, URLs)")
    is_active: bool = True

class DataSourceCreate(DataSourceBase):
    pass

class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[DataSourceProvider] = None
    type: Optional[DataSourceType] = None
    config_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class DataSourceResponse(DataSourceBase):
    id: uuid.UUID
    provider: Optional[DataSourceProvider] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
