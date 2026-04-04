import logging

logger = logging.getLogger(__name__)

def normalize_symbol(symbol: str) -> str:
    """
    Standardizes a symbol to ISO 4217 canonical format (BASEQUOTE).
    Example: 'XAU_USD', 'XAU/USD', 'XAU-USD', 'XAU USD' -> 'XAUUSD'
    """
    if not symbol:
        return ""
    # Strip all common separators
    return symbol.replace("_", "").replace("/", "").replace("-", "").replace(" ", "").upper()

def get_broker_format(symbol: str, broker_name: str) -> str:
    """
    Maps a canonical symbol (e.g., XAUUSD) to a broker-specific format.
    """
    symbol = normalize_symbol(symbol)
    broker_name = broker_name.upper()

    # Broker-Specific Mappings
    if "OANDA" in broker_name:
        # OANDA usually uses BASE_QUOTE (e.g., XAU_USD)
        if len(symbol) == 6:
            return f"{symbol[:3]}_{symbol[3:]}"
        elif symbol.startswith("XAU"): # XAUUSD case
            return "XAU_USD"
        return symbol

    # default to canonical for cTrader (e.g., XAUUSD)
    return symbol
