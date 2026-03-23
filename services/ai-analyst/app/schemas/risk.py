from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class CorrelationRequest(BaseModel):
    """
    Request for PCA-based correlation analysis.
    prices: Map of symbol -> list of float prices (D1 typically).
    """
    prices: Dict[str, List[float]] = Field(..., description="Map of symbol to historical price list")
    threshold: float = Field(default=0.6, description="Variance threshold for systemic alert")

class CorrelationResponse(BaseModel):
    status: str
    market_integration_score: float = Field(..., description="% variance explained by PC1")
    pc1_explained_variance: float
    top_factors_variance: List[float]
    asset_loadings: Dict[str, float] = Field(..., description="Loadings of each asset on PC1")
    systemic_alert: bool
    high_correlation_assets: List[str]
    reason: Optional[str] = None
