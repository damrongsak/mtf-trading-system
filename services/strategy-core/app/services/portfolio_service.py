import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from sqlalchemy import select, desc
from app.database import SessionLocal
from app.models.candle import Candle
from pypfopt import HRPOpt, risk_models, expected_returns

logger = logging.getLogger(__name__)

class PortfolioService:
    """
    Institutional Portfolio Engine.
    Uses Hierarchical Risk Parity (HRP) and Mean-Variance Optimization.
    """

    @staticmethod
    async def calculate_risk_parity_weights(prices_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculates weights using Hierarchical Risk Parity (HRP).
        HRP is more robust than MVO as it doesn't require expected returns
        and handles correlated assets gracefully by using a tree-based clustering.
        """
        try:
            if prices_df.empty or len(prices_df.columns) < 2:
                # Fallback to equal weight if not enough data
                symbols = prices_df.columns.tolist()
                if not symbols: return {}
                return {s: round(1.0 / len(symbols), 4) for s in symbols}

            # 1. Calculate Returns
            returns = prices_df.pct_change().dropna()
            
            # 2. HRP Optimization
            hrp = HRPOpt(returns)
            weights = hrp.optimize()
            
            # 3. Clean and normalize
            clean_weights = {s: round(float(w), 4) for s, w in weights.items()}
            
            logger.info(f"✅ HRP Optimization Complete: {clean_weights}")
            return clean_weights

        except Exception as e:
            logger.error(f"❌ Portfolio Optimization Error: {e}", exc_info=True)
            # Fallback to equal weights
            symbols = prices_df.columns.tolist()
            return {s: round(1.0 / len(symbols), 4) for s in symbols}

    @staticmethod
    async def get_portfolio_metrics(weights: Dict[str, float], prices_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates expected volatility and diversification ratio.
        """
        try:
            returns = prices_df.pct_change().dropna()
            cov_matrix = risk_models.sample_cov(prices_df)
            
            # Convert weights dict to vector
            w_vector = np.array([weights[s] for s in prices_df.columns])
            
            # Portfolio Volatility
            port_vol = np.sqrt(np.dot(w_vector.T, np.dot(cov_matrix, w_vector)))
            
            # Individual Volatilities (annualized)
            ind_vols = np.sqrt(np.diag(cov_matrix))
            weighted_vol_sum = np.sum(w_vector * ind_vols)
            
            # Diversification Ratio (Weighted Avg Vol / Portfolio Vol)
            div_ratio = weighted_vol_sum / port_vol if port_vol > 0 else 1.0

            return {
                "annualized_volatility": round(float(port_vol * np.sqrt(252)), 4),
                "diversification_ratio": round(float(div_ratio), 4),
                "n_assets": len(weights)
            }
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {}

    @staticmethod
    async def fetch_historical_prices(symbols: List[str], lookback_days: int = 252) -> pd.DataFrame:
        """
        Fetches D1 (Daily) candles for multiple symbols and aligns them into a single DataFrame.
        """
        all_prices = {}
        
        try:
            with SessionLocal() as db:
                for symbol in symbols:
                    stmt = select(Candle).where(
                        Candle.symbol == symbol,
                        Candle.timeframe == 'D1'  # Using Daily for portfolio optimization
                    ).order_by(desc(Candle.timestamp)).limit(lookback_days)
                    
                    results = db.execute(stmt).scalars().all()
                    if not results:
                        # Fallback for some symbols that might use 'D' instead of 'D1'
                        stmt = select(Candle).where(
                            Candle.symbol == symbol,
                            Candle.timeframe == 'D'
                        ).order_by(desc(Candle.timestamp)).limit(lookback_days)
                        results = db.execute(stmt).scalars().all()

                    if results:
                        # Convert to Series
                        prices = {c.timestamp.replace(tzinfo=None): float(c.close) for c in results}
                        all_prices[symbol] = pd.Series(prices)
                    else:
                        logger.warning(f"No daily history found for {symbol}")

            if not all_prices:
                return pd.DataFrame()

            # Align into single DataFrame
            df = pd.DataFrame(all_prices).sort_index()
            # Forward fill to handle missing values (holidays, etc)
            df = df.ffill().dropna()
            
            return df

        except Exception as e:
            logger.error(f"Error fetching historical prices: {e}")
            return pd.DataFrame()

    @staticmethod
    async def optimize_portfolio(symbols: List[str], lookback_days: int = 252) -> Dict[str, Any]:
        """
        High-level wrapper: Fetch -> Optimize -> Metrics.
        """
        df = await PortfolioService.fetch_historical_prices(symbols, lookback_days)
        if df.empty:
            return {"error": "No historical data available for selected symbols"}
            
        weights = await PortfolioService.calculate_risk_parity_weights(df)
        metrics = await PortfolioService.get_portfolio_metrics(weights, df)
        
        return {
            "weights": weights,
            "metrics": metrics,
            "lookback_days": lookback_days,
            "symbols_analyzed": list(df.columns)
        }

portfolio_service = PortfolioService()
