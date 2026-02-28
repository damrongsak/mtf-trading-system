import os
import pytest

# Set dummy environment variables before importing modules that use them
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1" # Point to potential local instance or just fake it

import sys
from unittest.mock import MagicMock, AsyncMock

# Mock redis BEFORE it's imported by app modules
mock_redis = MagicMock()
mock_redis.__path__ = []  # make it a package
mock_redis_asyncio = MagicMock()
mock_redis_asyncio.__path__ = []
mock_client = MagicMock()
mock_client.get = AsyncMock(return_value=None)
mock_client.set = AsyncMock()
mock_client.setex = AsyncMock()
mock_client.delete = AsyncMock()
mock_client.close = AsyncMock()
# Advanced PubSub Mock
mock_pubsub = MagicMock() # Use MagicMock as base
# Explicitly make methods AsyncMocks
mock_pubsub.subscribe = AsyncMock()
mock_pubsub.unsubscribe = AsyncMock()
mock_pubsub.psubscribe = AsyncMock()
mock_pubsub.punsubscribe = AsyncMock()
mock_pubsub.close = AsyncMock()

# Mock listen() to be an async generator
async def mock_listen():
    yield {'type': 'subscribe', 'channel': 'test', 'data': 1}
    # Then hang or stop
mock_pubsub.listen.return_value = mock_listen()

mock_client.pubsub.return_value = mock_pubsub
mock_redis_asyncio.from_url.return_value = mock_client
mock_redis.asyncio = mock_redis_asyncio
sys.modules["redis"] = mock_redis
sys.modules["redis.asyncio"] = mock_redis_asyncio
# Also mock fakeredis just in case
sys.modules["fakeredis"] = MagicMock()

from app.database import Base, engine
import sqlalchemy
from sqlalchemy.dialects import postgresql

# Monkeypatch PostgreSQL types for SQLite tests
def _patch_types():
    from sqlalchemy.types import JSON, String, TypeDecorator, Uuid
    
    class SQLiteUUID(TypeDecorator):
        impl = Uuid
        cache_ok = True
        def load_dialect_impl(self, dialect):
            if dialect.name == 'sqlite':
                return dialect.type_descriptor(String(36))
            return dialect.type_descriptor(Uuid())
        
        def process_bind_param(self, value, dialect):
            if value is None:
                return value
            if dialect.name == 'sqlite':
                return str(value)
            return value

        def process_result_value(self, value, dialect):
            if value is None:
                return value
            if dialect.name == 'sqlite':
                try:
                    return uuid.UUID(value)
                except (ValueError, TypeError):
                    return value
            return value

    postgresql.JSONB = JSON
    postgresql.UUID = SQLiteUUID
    
    # Also patch the main types and dialects etc.
    import sqlalchemy.types as types
    import sqlalchemy.dialects.postgresql.base as pg_base
    types.Uuid = SQLiteUUID
    pg_base.UUID = SQLiteUUID
    postgresql.base.UUID = SQLiteUUID

_patch_types()

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
    
    # Sanitize server_defaults for SQLite
    from sqlalchemy.sql.elements import TextClause
    from sqlalchemy import text
    
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.server_default is not None:
                if hasattr(column.server_default, 'arg'):
                    # Convert TextClause to string for inspection
                    sql = str(column.server_default.arg)
                    
                    original_sql = sql
                    
                    # Handle ::jsonb
                    if '::jsonb' in sql:
                        sql = sql.replace('::jsonb', '')
                    
                    # Handle gen_random_uuid()
                    if 'gen_random_uuid()' in sql:
                         # Drop the default completely for SQLite
                        column.server_default = None
                        continue

                    # Handle now() -> CURRENT_TIMESTAMP
                    if 'now()' in sql:
                        sql = 'CURRENT_TIMESTAMP'
                    
                    if sql != original_sql:
                        # Update the server_default with clean SQL
                        column.server_default.arg = text(sql)

    # Create tables
    Base.metadata.create_all(engine)
