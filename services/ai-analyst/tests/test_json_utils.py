import json
import uuid
from decimal import Decimal
from datetime import datetime, date
from app.utils.json import safe_json_dumps, UUIDDecimalEncoder

def test_safe_json_dumps():
    data = {
        "uuid": uuid.uuid4(),
        "decimal": Decimal("123.45"),
        "datetime": datetime(2026, 3, 8, 1, 0, 0),
        "date": date(2026, 3, 8),
        "nested": {
            "uuid": uuid.uuid4(),
            "list": [Decimal("1.0"), uuid.uuid4()]
        }
    }
    
    json_str = safe_json_dumps(data)
    parsed = json.loads(json_str)
    
    assert isinstance(parsed["uuid"], str)
    assert parsed["decimal"] == 123.45
    assert "2026-03-08T01:00:00" in parsed["datetime"]
    assert parsed["date"] == "2026-03-08"
    assert isinstance(parsed["nested"]["uuid"], str)
    assert parsed["nested"]["list"][0] == 1.0
    assert isinstance(parsed["nested"]["list"][1], str)

if __name__ == "__main__":
    try:
        test_safe_json_dumps()
        print("✅ test_safe_json_dumps passed!")
    except Exception as e:
        print(f"❌ test_safe_json_dumps FAILED: {e}")
        import traceback
        traceback.print_exc()
