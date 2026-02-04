from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

class RiskEngine:
    """
    Advanced Statistical Risk Engine using PCA (Principal Component Analysis).
    Identifies "Eigen-Portfolios" to detect hidden factor exposures.
    """

    def __init__(self):
        pass

    def calculate_eigen_risk(self, historical_prices: pd.DataFrame, threshold: float = 0.90) -> Dict[str, Any]:
        """
        Computes the First Principal Component (PC1) of the provided asset universe.
        PC1 typically represents the "Market Factor".
        
        :param historical_prices: DataFrame where columns are Symbols and index is Datetime.
        :param threshold: Correlation threshold to flag specific assets as "Systemic".
        :return: Dict containing variance explained, factor loadings, and risk flags.
        """
        try:
            # 1. Calculate Returns
            returns = historical_prices.pct_change().dropna()
            
            if returns.empty or len(returns.columns) < 2:
                return {
                    "status": "skipped",
                    "reason": "Insufficient data or assets for PCA"
                }

            # 2. Standardize
            scaler = StandardScaler()
            scaled_returns = scaler.fit_transform(returns)
            
            # 3. PCA
            # We only need the first few components
            n_components = min(len(returns.columns), 5)
            pca = PCA(n_components=n_components)
            pca.fit(scaled_returns)
            
            # 4. Extract Metrics
            explained_variance = pca.explained_variance_ratio_
            pc1_loadings = pca.components_[0] # Loadings of each asset on PC1
            
            # Map loadings back to symbols
            assets = returns.columns
            loadings_dict = {asset: float(load) for asset, load in zip(assets, pc1_loadings)}
            
            # 5. Detect high correlation to Market Factor (PC1)
            # A high loading implies the asset is just "following the herd"
            systemic_risk_assets = [
                asset for asset, load in loadings_dict.items() 
                if abs(load) > 0.5 # Heuristic cut-off for dominance, can be calibrated
            ]

            # Calculate Absorption Ratio (Systemic Risk Indicator)
            # Sum of variance explained by significant eigenvectors / Total Variance
            # Here we just use PC1 variance explained as a proxy for "Market Integration"
            market_integration_score = float(explained_variance[0])

            return {
                "status": "success",
                "market_integration_score": market_integration_score, # % variance explained by PC1
                "pc1_explained_variance": float(explained_variance[0]),
                "top_factors_variance": [float(x) for x in explained_variance],
                "asset_loadings": loadings_dict,
                "systemic_alert": market_integration_score > 0.60, # If PC1 explains > 60% of variance, high systemic risk
                "high_correlation_assets": systemic_risk_assets
            }

        except Exception as e:
            logger.error(f"PCA Calculation Error: {e}", exc_info=True)
            return {
                "status": "error",
                "reason": str(e)
            }
