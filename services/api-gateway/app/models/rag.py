from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum
from app.database import Base

class IngestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    INGESTED = "INGESTED"
    FAILED = "FAILED"

class LibraryBook(Base):
    __tablename__ = "library_books"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=True)
    author = Column(String, nullable=True)
    total_chunks = Column(Integer, nullable=False, default=0)
    ingestion_status = Column(Enum(IngestionStatus), default=IngestionStatus.PENDING)
    last_ingested_at = Column(DateTime, default=datetime.utcnow)
