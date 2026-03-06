import sys
import os
from sqlalchemy.orm import Session

# Add parent dir to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User
from app.security import get_password_hash

def seed_execution_user():
    db = SessionLocal()
    try:
        username = os.getenv("SYSTEM_USER", "execution_service")
        password = os.getenv("SYSTEM_PASSWORD", "servicepassword123")
        
        print(f"Seeding Execution Service User: {username}...")
        
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            user = User(
                username=username,
                email="execution@olympus.internal",
                password_hash=get_password_hash(password),
                is_active=True,
                is_superuser=True # Give it superuser to access all accounts for health check
            )
            db.add(user)
            db.commit()
            print(f"Successfully created user: {username}")
        else:
            print(f"User {username} already exists.")
            
    except Exception as e:
        print(f"Error seeding user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_execution_user()
