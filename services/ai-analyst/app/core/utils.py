from typing import Optional

def extract_auth_token(authorization: Optional[str]) -> Optional[str]:
    """Extract JWT token from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]
    return None
