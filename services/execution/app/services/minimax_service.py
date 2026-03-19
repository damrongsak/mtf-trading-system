from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class MinimaxService:
    """
    Implements the Minimax Regret Engine logic as defined in Layer 4 (Risk Citadel).
    Goal: Minimize the maximum possible regret (loss of capital or missed opportunity).
    """

    @staticmethod
    def calculate_regret(
        risk_usd: float,
        reward_usd: float,
        confidence: float,
        pain_threshold: float,
        volatility_multiplier: float = 1.0
    ) -> Tuple[bool, float, str]:
        """
        Validates a trade based on Minimax Regret logic.
        
        :param risk_usd: Potential loss if trade hits SL.
        :param reward_usd: Potential profit if trade hits TP.
        :param confidence: Signal confidence (0.0 to 1.0).
        :param pain_threshold: User's maximum psychological pain threshold (USD).
        :param volatility_multiplier: Multiplier based on ATR regime (e.g. 1.0=Normal, 1.5=High Vol).
        :return: (is_allowed, regret_value, reason)
        """
        
        # 1. Calculate Regret(Trade) = Potential Loss
        # We assume if we lose, we lose the full Risk amount.
        # Adjusted by volatility? Spec: "Inputs: Signal Confidence, Market Volatility..."
        # If Volatility is high, the "Emotional Pain" of a loss might be higher or probability of slippage higher.
        # Let's scale perceived risk by volatility_multiplier logic if needed. 
        # For now, strict USD Regret.
        regret_trade = risk_usd * volatility_multiplier
        
        # 2. Calculate Regret(NoTrade) = Potential Missed Profit
        # If we don't trade and it wins, we regret missing the reward.
        # Weighted by confidence? If I'm 90% confident and miss it, regret is high.
        # If I'm 10% confident and miss it, regret is low.
        regret_no_trade = reward_usd * confidence
        
        # 3. worst Case Regret
        worst_case_regret = max(regret_trade, regret_no_trade)
        
        # 4. Decision
        if worst_case_regret > pain_threshold:
            reason = (
                f"Regret {worst_case_regret:.2f} (Max of Risk={regret_trade:.2f}, Missed={regret_no_trade:.2f}) "
                f"exceeds Pain Threshold {pain_threshold:.2f}"
            )
            return False, worst_case_regret, reason
            
        return True, worst_case_regret, "OK"
