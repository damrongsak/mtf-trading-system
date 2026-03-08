from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

@dataclass
class AccountState:
    balance: Decimal
    equity: Decimal
    margin_used: Decimal
    open_positions: int
    
    @property
    def free_margin(self) -> Decimal:
        return self.equity - self.margin_used
    
    @property
    def margin_level(self) -> Optional[Decimal]:
        if self.margin_used == 0:
            return None
        return (self.equity / self.margin_used) * 100

@dataclass 
class TradeProposal:
    symbol: str
    direction: str  # 'BUY' | 'SELL'
    lot_size: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal

class EconomicSanityGate:
    """
    Hard constraints - 100% deterministic, no LLM involved.
    This gate acts as the final safety check before trade execution.
    """
    
    # Default thresholds (should ideally be loaded from fund/broker config)
    MAX_LOT_SIZE = Decimal("0.1")      # Initial testing cap
    MIN_MARGIN_LEVEL = Decimal("150")  # Stop out level + buffer
    MAX_DAILY_LOSS_PCT = Decimal("2")  # 2% of account
    MAX_CONCURRENT_TRADES = 3
    RISK_OF_RUIN_LIMIT_PCT = Decimal("6")  # Max 6% total drawdown exposure
    
    def __init__(self, account: AccountState, daily_pnl: Decimal = Decimal("0")):
        self.account = account
        self.daily_pnl = daily_pnl
    
    def validate_proposal(self, proposal: TradeProposal) -> Tuple[bool, List[str]]:
        """
        Validates a trade proposal against hard deterministic rules.
        Returns (is_safe, list_of_violations)
        """
        violations = []
        
        # 1. Lot size check
        if proposal.lot_size > self.MAX_LOT_SIZE:
            violations.append(f"LOT_EXCEEDED: {proposal.lot_size} > {self.MAX_LOT_SIZE}")
        
        # 2. Margin level check
        if self.account.margin_level and self.account.margin_level < self.MIN_MARGIN_LEVEL:
            violations.append(f"MARGIN_LEVEL_LOW: {self.account.margin_level:.2f}% < {self.MIN_MARGIN_LEVEL}%")
        
        # 3. Daily loss check
        if abs(self.daily_pnl) > self.account.balance * (self.MAX_DAILY_LOSS_PCT / 100):
            violations.append(f"DAILY_LOSS_LIMIT: {self.daily_pnl} exceeds {self.MAX_DAILY_LOSS_PCT}% limit")
        
        # 4. Concurrent positions check
        if self.account.open_positions >= self.MAX_CONCURRENT_TRADES:
            violations.append(f"MAX_POSITIONS_REACHED: {self.account.open_positions} >= {self.MAX_CONCURRENT_TRADES}")
        
        # 5. Risk-of-Ruin / Total Exposure check
        exposure = self._calculate_exposure_usd(proposal)
        if exposure > self.account.balance * (self.RISK_OF_RUIN_LIMIT_PCT / 100):
            violations.append(f"RISK_OF_RUIN: Exposure {exposure:.2f} USD > {self.RISK_OF_RUIN_LIMIT_PCT}% of balance")
        
        # 6. SL/TP sanity
        self._check_price_sanity(proposal, violations)
        
        is_safe = len(violations) == 0
        if not is_safe:
            logger.warning(f"Economic Sanity Gate blocked proposal for {proposal.symbol}: {violations}")
            
        return is_safe, violations
    
    def _check_price_sanity(self, proposal: TradeProposal, violations: List[str]):
        """Internal checks for price logic errors"""
        if proposal.stop_loss == proposal.entry_price:
            violations.append("SL_SAME_AS_ENTRY")
        if proposal.take_profit == proposal.entry_price:
            violations.append("TP_SAME_AS_ENTRY")
            
        if proposal.direction.upper() == "BUY":
            if proposal.stop_loss > proposal.entry_price:
                violations.append("LONG_SL_ABOVE_ENTRY")
            if proposal.take_profit < proposal.entry_price:
                violations.append("LONG_TP_BELOW_ENTRY")
        elif proposal.direction.upper() == "SELL":
            if proposal.stop_loss < proposal.entry_price:
                violations.append("SHORT_SL_BELOW_ENTRY")
            if proposal.take_profit > proposal.entry_price:
                violations.append("SHORT_TP_ABOVE_ENTRY")

    def _calculate_exposure_usd(self, proposal: TradeProposal) -> Decimal:
        """
        Calculates worst-case loss in USD if Stop Loss is hit.
        Simplified version for XAUUSD (100 oz per lot).
        """
        # In institutional version, this should fetch contract size from market_symbols registry
        contract_size = Decimal("100") # Default for XAUUSD
        price_diff = abs(proposal.entry_price - proposal.stop_loss)
        return price_diff * proposal.lot_size * contract_size
