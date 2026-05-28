
import os
import sys
from datetime import datetime, timedelta, timezone
from jose import jwt

# Mirroring app/security.py
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

def create_access_token(username: str, expires_delta: timedelta = None):
    to_encode = {"sub": username}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=43200) # 30 days
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    token = create_access_token(username)
    print(token)
