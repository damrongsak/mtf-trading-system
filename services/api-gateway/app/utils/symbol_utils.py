import json
from typing import Any, Union

def normalize_symbol(symbol: Any) -> str:
    """
    Normalizes a symbol into a canonical uppercase format without slashes.
    Ensures 'XAU/USD', 'XAU_USD', and 'XAUUSD' are treated consistently.
    """
    if not symbol:
        return ""
    
    raw = ""
    if isinstance(symbol, str):
        # Handle JSON strings if needed
        clean_symbol = symbol.strip()
        if clean_symbol.startswith("{") and clean_symbol.endswith("}"):
            try:
                data = json.loads(clean_symbol)
                for key in ["symbol", "SYMBOL", "instrument", "INSTRUMENT"]:
                    if key in data:
                        raw = str(data[key])
                        break
            except:
                pass
        
        if not raw:
            raw = clean_symbol
    
    elif isinstance(symbol, dict):
        for key in ["symbol", "SYMBOL", "instrument", "INSTRUMENT"]:
            if key in symbol:
                raw = str(symbol[key])
                break
    
    if not raw:
        raw = str(symbol)

    # Canonical normalization: 
    # 1. Uppercase
    # 2. Remove slashes (used in legacy or display formats)
    # 3. We keep underscores by default for OANDA compatibility, 
    # but market.py should check both stripped and underscored versions.
    return raw.upper().replace("/", "").replace("-", "")
