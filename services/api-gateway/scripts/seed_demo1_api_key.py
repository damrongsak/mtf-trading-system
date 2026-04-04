from app.database import SessionLocal
from app.models.api_key import ApiKey
from app.utils.crypto import encrypt_data
import uuid
import os

def seed_demo1_key():
    db = SessionLocal()
    # demo1 UID resolved from live DB
    user_id = "e2079cc2-11d0-4e8f-9b69-49ea0ba7cd96" 
    test_key = "ak_test_demo1_smc_v24"
    test_secret = "sk_test_demo1_secret_999"

    # Check if already exists
    existing = db.query(ApiKey).filter(ApiKey.api_key == test_key).first()
    if existing:
        print(f"API Key {test_key} already exists. Using existing.")
        return

    # Secret is stored as encrypt_data({"secret": test_secret})
    encrypted_secret = encrypt_data({"secret": test_secret})

    key_entry = ApiKey(
        user_id=uuid.UUID(user_id),
        name="Demo1 3rd Party Key",
        api_key=test_key,
        api_secret=encrypted_secret,
        is_active=True
    )
    db.add(key_entry)
    db.commit()
    print(f"✅ Created API Key: {test_key} for user demo1")
    print(f"   Secret: {test_secret} (Keep this for the test script)")

if __name__ == "__main__":
    seed_demo1_key()
