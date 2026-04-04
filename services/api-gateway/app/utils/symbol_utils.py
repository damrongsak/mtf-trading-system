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
    # 2. Remove all separators (ISO 4217 Commercial Standard)
    return raw.upper().replace("/", "").replace("_", "").replace("-", "").replace(" ", "")

def get_broker_format(symbol: str, broker: str = "OANDA") -> str:
    """
    Translates internal 'XAUUSD' into broker-specific formats.
    """
    normalized = normalize_symbol(symbol)
    
    # OANDA prefers 6-7 chars with underscores for FX/Metals
    if broker.upper() == "OANDA":
        if normalized == "XAUUSD": return "XAU_USD"
        if normalized == "EURUSD": return "EUR_USD"
        if normalized == "USDJPY": return "USD_JPY"
        if normalized == "GBPUSD": return "GBP_USD"
        if len(normalized) == 6:
            return f"{normalized[:3]}_{normalized[3:]}"
            
    # CTRADER usually uses just the symbol or specific numeric ID (handled via DB details)
    return normalized
