from typing import Optional

def extract_auth_token(authorization: Optional[str]) -> Optional[str]:
    """Extract JWT token from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]
    return None

import json
from typing import Any

def parse_tool_input(input_data: Any) -> dict:
    """Robustly parse input_data into a dictionary."""
    if isinstance(input_data, dict):
        return input_data
    if isinstance(input_data, str) and input_data.strip():
        try:
            return json.loads(input_data)
        except:
            # If it's a raw string (e.g. "XAUUSD"), wrap it
            return {"symbol": input_data.strip()}
    return {}
