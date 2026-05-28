
import sys
import os

# Add app directory to path
sys.path.append("/app")

from app.security import create_access_token
from datetime import timedelta

# Generate a token for admin that lasts 1 hour
token = create_access_token(data={"sub": "admin"}, expires_delta=timedelta(hours=1))
print(token)
