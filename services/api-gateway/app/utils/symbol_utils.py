import json
from typing import Any, Union

def normalize_symbol(symbol: Any) -> str:
    """
    Normalizes a symbol which might be a raw string or a JSON-encoded string/object.
    Commonly used to fix issues where frontend passes {"SYMBOL": "XAUUSD"} as a string.
    """
    if not symbol:
        return ""
    
    if isinstance(symbol, str):
        # Check if it's a JSON string
        clean_symbol = symbol.strip()
        if clean_symbol.startswith("{") and clean_symbol.endswith("}"):
            try:
                data = json.loads(clean_symbol)
                # Try common keys
                for key in ["symbol", "SYMBOL", "instrument", "INSTRUMENT"]:
                    if key in data:
                        return str(data[key]).upper().replace("/", "_")
            except:
                pass
        
        # Regular string
        return clean_symbol.upper().replace("/", "_")
    
    if isinstance(symbol, dict):
        for key in ["symbol", "SYMBOL", "instrument", "INSTRUMENT"]:
            if key in symbol:
                return str(symbol[key]).upper().replace("/", "_")
    
    return str(symbol).upper().replace("/", "_")
