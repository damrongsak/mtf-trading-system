
from cryptography.fernet import Fernet
import os
import json
import base64
from functools import lru_cache

# Generate a key if not present (for dev only - in prod this must be fixed)
# Ideally: SETTINGS_ENCRYPTION_KEY=... in .env
# Key generation: Fernet.generate_key().decode()

@lru_cache(maxsize=1)
def get_cipher():
    key = os.getenv("SETTINGS_ENCRYPTION_KEY")
    if not key:
        # Fallback for development ONLY - insecure for production
        # In real dev env, should be set.
        # Check if we are testing
        if os.getenv("TESTING", "False") == "True":
             key = Fernet.generate_key().decode()
        else:
             # Try to share the same default as api-gateway or fail
             raise ValueError("SETTINGS_ENCRYPTION_KEY environment variable is not set")
    return Fernet(key.encode())

def encrypt_data(data: dict) -> str:
    """Encrypts a dictionary to a secure string."""
    cipher = get_cipher()
    json_bytes = json.dumps(data).encode('utf-8')
    encrypted_bytes = cipher.encrypt(json_bytes)
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def decrypt_data(encrypted_str: str) -> dict:
    """Decrypts a secure string back to a dictionary."""
    cipher = get_cipher()
    encrypted_bytes = base64.b64decode(encrypted_str)
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return json.loads(decrypted_bytes.decode('utf-8'))
