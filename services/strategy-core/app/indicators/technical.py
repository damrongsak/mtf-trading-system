import pandas as pd
# import pandas_ta as ta

def calculate_indicator(df: pd.DataFrame, strategy: str = "Common") -> pd.DataFrame:
    """
    Calculate indicators using pandas-ta.
    supports executing a 'Strategy' (pandas_ta concept) or specific indicators.
    """
    # Stubbed due to removal of pandas-ta
    # if strategy == "All":
    #     df.ta.strategy("All")
    # elif strategy == "Common":
    #     # Example common strategy using direct calls
    #     df.ta.sma(length=50, append=True)
    #     df.ta.sma(length=200, append=True)
    #     df.ta.rsi(append=True)
    #     df.ta.atr(length=14, append=True)
    
    return df
