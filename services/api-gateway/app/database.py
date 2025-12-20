"""
Database configuration and connection management.
Follows the data model specification in specs/03_data_model.yaml
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

# Database URL from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://trader:trader@localhost:5432/mtf_db"
)

# Create SQLAlchemy engine
# NullPool is used for better compatibility with async operations
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=True if os.getenv("DEBUG") == "true" else False
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Used in FastAPI route dependencies.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    This should typically be done via Alembic migrations.
    """
    Base.metadata.create_all(bind=engine)
