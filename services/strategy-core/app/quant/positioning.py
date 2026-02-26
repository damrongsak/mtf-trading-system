import logging
import pandas as pd
from typing import Dict, Any, Optional
from sqlalchemy import text
from app.database import SessionLocal
from app.config_cache import config_cache

logger = logging.getLogger(__name__)

class PositioningEngine:
    """
    Institutional Quant Layer: Positioning Model.
    Handles hierarchical risk budget and dynamic lot sizing.
    """

    def __init__(self, 
                 default_risk_percentage: float = 0.01, 
                 default_max_risk_usd: float = 10.0):
        self.default_risk_percentage = default_risk_percentage
        self.default_max_risk_usd = default_max_risk_usd

    def get_risk_profile(self, strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves hierarchical risk configuration:
        Strategy -> BrokerAccount -> Fund -> System Default
        """
        config = {
            "risk_percentage": self.default_risk_percentage,
            "max_risk_usd": self.default_max_risk_usd,
            "source": "system_default",
            "kelly_fraction_used": None,
            "historical_metrics": None
        }

        if not strategy_id:
            return config

        # 1. HFT Optimization: Check Cache First
        cached_profile = config_cache.get_config(f"risk_profile_{strategy_id}")
        if cached_profile:
            return cached_profile

        try:
            with SessionLocal() as db:
                # 1. Fetch Strategy and its linked IDs
                # We use raw SQL to avoid model dependency issues in strategy-core
                query = text("""
                    SELECT 
                        s.risk_settings as strategy_risk,
                        s.last_backtest_result as strategy_backtest,
                        f.risk_percentage as fund_risk_pct,
                        f.max_risk_per_trade as fund_max_risk,
                        ba.risk_settings as account_risk
                    FROM strategies s
                    LEFT JOIN funds f ON s.fund_id = f.id
                    LEFT JOIN broker_accounts ba ON s.broker_account_id = ba.id
                    WHERE s.id = :strategy_id
                """)
                result = db.execute(query, {"strategy_id": strategy_id}).fetchone()

                if result:
                    # Merge Logic (Lowest in hierarchy wins)
                    
                    # Fund Levels (Highest / Broadest)
                    if result.fund_risk_pct is not None:
                        config["risk_percentage"] = float(result.fund_risk_pct)
                        config["source"] = "fund"
                    if result.fund_max_risk is not None:
                        config["max_risk_usd"] = float(result.fund_max_risk)

                    # Account Levels
                    account_risk = result.account_risk or {}
                    if account_risk.get("risk_percentage"):
                        config["risk_percentage"] = float(account_risk["risk_percentage"])
                        config["source"] = "broker_account"
                    if account_risk.get("max_risk_usd"):
                        config["max_risk_usd"] = float(account_risk["max_risk_usd"])

                    # Strategy Levels (Narrowest / Specific)
                    strategy_risk = result.strategy_risk or {}
                    if strategy_risk.get("risk_percentage"):
                        config["risk_percentage"] = float(strategy_risk["risk_percentage"])
                        config["source"] = "strategy"
                    if strategy_risk.get("max_risk_usd"):
                        config["max_risk_usd"] = float(strategy_risk["max_risk_usd"])

                    # Extract Historical Metrics for Kelly
                    if result.strategy_backtest:
                        bt = result.strategy_backtest
                        config["historical_metrics"] = {
                            "win_rate": float(bt.get("win_rate", 0)),
                            "profit_factor": float(bt.get("profit_factor", 0)),
                            "avg_win": float(bt.get("avg_win", 0)),
                            "avg_loss": abs(float(bt.get("avg_loss", 0))) if bt.get("avg_loss") else 0
                        }

                # Cache the compiled profile to save DB hits in HFT path (5 mins TTL emulation)
                config_cache.set_config(f"risk_profile_{strategy_id}", config)

        except Exception as e:
            logger.error(f"Error fetching hierarchical risk profile: {e}")
            # Fallback to system defaults already in 'config'

        return config

    def calculate_lot_size(self, 
                           symbol: str,
                           entry_price: float,
                           stop_loss: float,
                           equity: float,
                           risk_map: Dict[str, Any],
                           strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Dynamic Position Sizing:
        Size = BaseSize * RegimeMultiplier * EdgeScore * GammaFactor
        """
        # 1. Get Risk Profile (Cached)
        risk_profile = self.get_risk_profile(strategy_id)
        
        # 2. Base Risk Calculation (Default vs Kelly)
        risk_pct = risk_profile["risk_percentage"]
        kelly_fraction_used = None
        
        historical = risk_profile.get("historical_metrics")
        if historical:
            w = historical.get("win_rate", 0)
            avg_win = historical.get("avg_win", 0)
            avg_loss = historical.get("avg_loss", 0)
            
            # Kelly = W - [ (1 - W) / R ]
            if avg_loss > 0 and w > 0:
                r = avg_win / avg_loss
                if r > 0:
                    kelly_pct = w - ((1 - w) / r)
                    if kelly_pct > 0:
                        # Apply Fractional Kelly (Half-Kelly for safety)
                        fractional_multiplier = 0.5 
                        dynamic_risk = kelly_pct * fractional_multiplier
                        
                        # Use Kelly if it's less aggressive than the hardcoded risk, 
                        # or allow it to override up to a safe cap (e.g. max 5%)
                        safe_cap = 0.05
                        risk_pct = min(dynamic_risk, safe_cap)
                        kelly_fraction_used = fractional_multiplier
                        logger.info(f"Applying Kelly Criterion: W={w:.2f}, R={r:.2f} -> Raw K={kelly_pct:.3f}, Fraction={fractional_multiplier}, Final %={risk_pct:.3f}")
                    else:
                        logger.warning(f"Negative Kelly Edge (W={w:.2f}, R={r:.2f}). Fallback to minimum risk 0.1%")
                        risk_pct = 0.001 # Absolute minimum
            else:
                logger.debug("Incomplete historical metrics for Kelly. Using static risk_percentage.")

        max_risk_usd = risk_profile["max_risk_usd"]

        # 3. Base Risk Amount (USD)
        risk_amount_usd = equity * risk_pct
        
        # Hard Cap by Fund/Account Limit
        final_risk_usd = min(risk_amount_usd, max_risk_usd)

        # 3. Calculate Base Size (Units)
        # Assuming Gold/Forex distance
        risk_per_point = abs(entry_price - stop_loss)
        if risk_per_point == 0:
            return {"error": "Invalid Stop Loss (distance is zero)"}

        # For XAUUSD, 1 unit = $1 move if it's a standard CFD.
        # But we use the formula: Size = RiskUSD / RiskPerPoint
        base_size = final_risk_usd / risk_per_point

        # 4. Apply Quant Weighting
        regime = risk_map.get("context", {}).get("regime")
        edge_score = risk_map.get("edge_score", 0.5)
        gamma = risk_map.get("layers", {}).get("gamma_bias", "NEUTRAL")

        # Regime Multiplier
        regime_mult = 1.0
        if "TRENDING" in str(regime):
            regime_mult = 1.2
        elif regime == "RANGING":
            regime_mult = 0.6
        elif regime == "UNSTABLE":
            regime_mult = 0.4

        # Gamma Factor
        gamma_factor = 1.0
        if gamma == "NEGATIVE":
            gamma_factor = 1.1 # Favoring acceleration
        elif gamma == "POSITIVE":
            gamma_factor = 0.8 # De-risking acceleration

        # Final Size Calculation
        # AdjustedSize = BaseSize * RegimeMult * EdgeScore * GammaFactor
        adjusted_size = base_size * regime_mult * edge_score * gamma_factor

        return {
            "symbol": symbol,
            "base_risk_usd": round(risk_amount_usd, 2),
            "effective_risk_usd": round(final_risk_usd, 2),
            "lot_size_units": round(adjusted_size, 4),
            "risk_per_point": round(risk_per_point, 4),
            "multipliers": {
                "regime": regime_mult,
                "edge": edge_score,
                "gamma": gamma_factor
            },
            "risk_profile_source": risk_profile["source"],
            "kelly_fraction_used": kelly_fraction_used
        }

positioning_engine = PositioningEngine()
