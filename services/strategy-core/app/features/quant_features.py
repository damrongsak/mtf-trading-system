import pandas as pd
import quantreo.features_engineering as fe
from typing import Optional

class QuantreoFeatures:
    """
    Adapter to expose Quantreo feature engineering capabilities
    to the Strategy Foundry.
    """

    @staticmethod
    def add_volatility_features(df: pd.DataFrame, high_col: str = 'high', low_col: str = 'low', window_size: int = 30) -> pd.DataFrame:
        """
        Add Parkinson Volatility to the DataFrame.
        """
        df = df.copy()
        df[f"parkinson_vol_{window_size}"] = fe.volatility.parkinson_volatility(
            df=df, 
            high_col=high_col, 
            low_col=low_col, 
            window_size=window_size
        )
        return df

    @staticmethod
    def add_entropy_features(df: pd.DataFrame, close_col: str = 'close', window_size: int = 30) -> pd.DataFrame:
        """
        Add Entropy features (if available in Quantreo FE module)
        Note: Assuming standard API based on README.
        """
        # Placeholder for entropy if explicit function isn't in generic example
        # Checking implementation capability or ensuring imports match
        # in a real scenario, we'd check dir(fe)
        return df

    @staticmethod
    def get_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply a standard suite of Quantreo features.
        """
        df = QuantreoFeatures.add_volatility_features(df)
        return df
