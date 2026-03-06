from sqlalchemy import text
from app.database import SessionLocal

def check_db():
    session = SessionLocal()
    try:
        # List all databases
        stmt = text("SELECT datname FROM pg_database WHERE datistemplate = false")
        result = session.execute(stmt)
        dbs = [row[0] for row in result.fetchall()]
        print("\n--- Databases ---")
        for db in dbs:
            print(db)
            
        # Get current database name
        stmt = text("SELECT current_database()")
        result = session.execute(stmt)
        curr_db = result.fetchone()[0]
        print(f"\n--- Current Database: {curr_db} ---")
    finally:
        session.close()

if __name__ == "__main__":
    check_db()
