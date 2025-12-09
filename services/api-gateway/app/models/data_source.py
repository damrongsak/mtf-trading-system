from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, comment="Provider name (e.g., OANDA, BINANCE)")
    type = Column(String, nullable=False, comment="Type of data source (e.g., api, csv, db)")
    config_json = Column(JSONB, nullable=False, comment="Connection details (API keys, URLs) - Encrypted in app")
    schema_json = Column(JSONB, nullable=True, comment="Expected data schema (e.g., column names for CSV, API response structure)")
    is_active = Column(Boolean, default=True)
