import os
import contextlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    if "sqlite" in DATABASE_URL:
        from sqlalchemy.pool import StaticPool
        kwargs = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in DATABASE_URL:
            kwargs["poolclass"] = StaticPool
        engine = create_engine(DATABASE_URL, **kwargs)
    else:
        engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # Dummy for tests or when DB not needed
    engine = None
    SessionLocal = sessionmaker(autocommit=False, autoflush=False)

Base = declarative_base()

@contextlib.contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
