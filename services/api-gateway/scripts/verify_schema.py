import sys
import os

# Add the parent directory to sys.path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from app.database import Base, DATABASE_URL
import app.models  # Ensure all models are loaded into Base.metadata

def verify_schema():
    """
    Compares the SQLAlchemy models (metadata) with the actual database schema
    using Alembic's autogenerate comparison.
    """
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            mc = MigrationContext.configure(connection)
            diff = compare_metadata(mc, Base.metadata)
            
            if not diff:
                print("\n✅ Schema is in sync with models.")
                return True
            else:
                print("\n❌ Schema drift detected!")
                print("The following discrepancies were found between models and DB:")
                for change in diff:
                    print(f"  - {change}")
                
                print("\nAction required: Run 'alembic revision --autogenerate' and 'alembic upgrade head'")
                return False
    except Exception as e:
        print(f"\n❌ Error connecting to database: {e}")
        return False

if __name__ == "__main__":
    success = verify_schema()
    sys.exit(0 if success else 1)
