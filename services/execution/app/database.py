
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://trader:trader@localhost:5432/mtf_db"
)

# Use NullPool for compatibility with async frameworks if needed, or QueuePool for production
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
