import os
import pytest

# Set dummy DATABASE_URL before importing modules that use it
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

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
                return dialect.type_descriptor(String())
            return dialect.type_descriptor(Uuid())

    postgresql.JSONB = JSON
    postgresql.UUID = SQLiteUUID

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
