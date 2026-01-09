import os
import pytest

# Set dummy DATABASE_URL before importing modules that use it
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base, engine
import app.models  # Register models
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Define Mock Schema matching ForeignKey expectations
class MockUser(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String)

class MockPlugin(Base):
    __tablename__ = "plugins" 
    __table_args__ = {"extend_existing": True}
    id = Column(String, primary_key=True)


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """
    Ensure environment variables are set for testing.
    """
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    # Create tables
    Base.metadata.create_all(engine)
