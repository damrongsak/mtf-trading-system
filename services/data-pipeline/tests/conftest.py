import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
import uuid

# Use in-memory SQLite for speed
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Fix for SQLite not supporting Postgres-specific JSONB
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Monkeypatch app.database to use the testing engine/session
import app.database
app.database.engine = engine
app.database.SessionLocal = TestingSessionLocal

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh database for each test function.
    """
    # Import all models to ensure they are registered with Base.metadata
    from app.models.candle import Candle
    from app.models.market import MarketSymbol, MarketCategory
    from app.models.data_source import DataSource
    # from app.models.open_interest import OpenInterest # Ensure this exists if testing it
    
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

from app.models.market import MarketSymbol, MarketCategory

@pytest.fixture
def mock_market_symbol(db_session):
    # 1. Create Category
    cat = MarketCategory(name="Forex", order_index=1)
    db_session.add(cat)
    db_session.flush()
    
    # 2. Create DataSource
    ds = DataSource(name="OANDA", provider="OANDA", type="api", config_json={})
    db_session.add(ds)
    db_session.flush()
    
    # 3. Create Symbol with Category
    ms = MarketSymbol(
        symbol="EUR_USD", 
        display_name="Euro vs US Dollar", 
        category_id=cat.id, # Link to category
        data_source_id=ds.id,
        is_active=True
    )
    db_session.add(ms)
    db_session.flush()
    db_session.refresh(ms)
    return ms
