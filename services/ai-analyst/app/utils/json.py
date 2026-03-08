import json
import uuid
from decimal import Decimal
from datetime import datetime, date

class UUIDDecimalEncoder(json.JSONEncoder):
    """
    Robust JSON Encoder that handles:
    - uuid.UUID -> str
    - decimal.Decimal -> float
    - datetime/date -> ISO string
    """
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def safe_json_dumps(obj, indent=None):
    """Helper to dump JSON with UUID/Decimal support."""
    return json.dumps(obj, cls=UUIDDecimalEncoder, indent=indent)
