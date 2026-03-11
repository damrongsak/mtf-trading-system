from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
from app.services.portfolio_service import portfolio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["Risk Management"])

class RiskCheckRequest(BaseModel):
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    account_balance: Optional[float] = Field(None, description="Account Balance in USD")
    risk_percentage: Optional[float] = Field(1.0, description="Risk per trade in % (default 1%)")
    risk_usd: Optional[float] = Field(None, description="Risk in USD (overrides percentage)")
    
class RiskCheckResponse(BaseModel):
    symbol: str
    risk_reward_ratio: float
    position_size_units: float
    position_size_lots: float
    risk_amount_usd: float
    potential_profit_usd: float
    is_safe: bool
    warnings: list[str] = []

@router.post("/check", response_model=Dict[str, Any])
async def calculate_risk(req: RiskCheckRequest = Body(...)):
    """
    Calculate position size and Risk:Reward ratio.
    """
    try:
        warnings = []
        entry = req.entry_price
        sl = req.stop_loss
        tp = req.take_profit
        
        if entry <= 0 or sl <= 0:
            raise HTTPException(status_code=400, detail="Prices must be positive")
            
        # 1. Determine Direction
        direction = "LONG" if entry > sl else "SHORT"
        
        # 2. Calculate Stop Loss Distance
        sl_dist = abs(entry - sl)
        if sl_dist == 0:
             raise HTTPException(status_code=400, detail="Stop Loss cannot be equal to Entry")
             
        # 3. Calculate Risk Amount
        risk_amt = 0.0
        if req.risk_usd:
            risk_amt = req.risk_usd
        elif req.account_balance:
            risk_amt = req.account_balance * (req.risk_percentage / 100.0)
        else:
            # Default fallback if no balance provided: assume $100 risk for calculation
            risk_amt = 100.0 
            warnings.append("No account balance provided. Calculated based on $100 risk.")

        # 4. Calculate Position Size
        # Value per unit. For XAUUSD, 1 unit = 1 oz. Price move of $1 = $1 PnL per unit.
        # Forex pairs are different, but let's assume standard USD counter-currency pairs or XAUUSD for now.
        # TODO: Add robust pip-value calculation service. For now, we use a simplified model.
        
        # Risk = Size * Distance
        # Size = Risk / Distance
        size_units = risk_amt / sl_dist
        
        # Standard Lot = 100,000 units (Forex) or 100 oz (Gold)?
        # For XAUUSD, standard lot is often 100 oz.
        # Let's assume 100 for XAUUSD and 100,000 for Forex.
        standard_lot_size = 100 if "XAU" in req.symbol.upper() else 100000
        size_lots = size_units / standard_lot_size
        
        # 5. Calculate R:R
        rr = 0.0
        profit_amt = 0.0
        if tp:
            tp_dist = abs(tp - entry)
            # Verify TP direction
            if direction == "LONG" and tp <= entry:
                warnings.append("Take Profit is below Entry for LONG trade.")
            elif direction == "SHORT" and tp >= entry:
                warnings.append("Take Profit is above Entry for SHORT trade.")
            
            rr = tp_dist / sl_dist
            profit_amt = size_units * tp_dist
        
        # 6. Safety Checks
        is_safe = True
        if rr > 0 and rr < 1.0:
            is_safe = False
            warnings.append(f"Poor Risk:Reward Ratio ({rr:.2f}). Target > 1.5")
        
        # Return Check Result
        return {
            "data": {
                "symbol": req.symbol,
                "direction": direction,
                "risk_reward_ratio": round(rr, 2),
                "position_size": {
                    "units": round(size_units, 2),
                    "lots": round(size_lots, 2),
                    "standard_lot_size": standard_lot_size
                },
                "financials": {
                    "risk_usd": round(risk_amt, 2),
                    "profit_usd": round(profit_amt, 2) if tp else 0.0,
                    "account_balance": req.account_balance
                },
                "is_safe": is_safe,
                "warnings": warnings
            }
        }

    except Exception as e:
        logger.error(f"Risk calc error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PortfolioParityRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols to optimize (e.g. ['XAUUSD', 'EURUSD'])")
    lookback_days: int = Field(252, description="Lookback window for history (market days)")

@router.post("/parity", response_model=Dict[str, Any])
async def calculate_portfolio_parity(req: PortfolioParityRequest = Body(...)):
    """
    Calculate Institutional Risk Parity weights for a multi-asset portfolio.
    """
    try:
        result = await portfolio_service.optimize_portfolio(
            symbols=req.symbols,
            lookback_days=req.lookback_days
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {"data": result}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Portfolio parity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
