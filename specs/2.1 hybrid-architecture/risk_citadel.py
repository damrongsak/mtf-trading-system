import numpy as np
from typing import Dict, Any, List

class RiskCitadel:
    """
    MTF Olympus - L4 Risk Layer
    Implements Game Theoretic Risk Management using Minimax Regret.
    Integrates Bayesian probabilities from L3 into execution decisions.
    """

    def __init__(self, risk_appetite: float = 0.5):
        """
        :param risk_appetite: 0.0 (Ultra-conservative) to 1.0 (Aggressive)
        """
        self.risk_appetite = risk_appetite

    def calculate_minimax_decision(self, 
                                 prob_assignment: float, 
                                 premium_capture: float, 
                                 max_loss_on_assignment: float) -> Dict[str, Any]:
        """
        Calculates the 'Regret' matrix for two states: 
        State A (Stock stays OTM) and State B (Stock goes ITM/Assigned).
        
        Decisions: 
        D1: Execute Trade (Sell Put)
        D2: Sit in Cash (Avoid Trade)
        """
        
        # 1. Utility Matrix (Potential Profit/Loss)
        # Rows: Decisions [Trade, Cash]
        # Cols: Outcomes [No Assignment, Assignment]
        utility_matrix = np.array([
            [premium_capture, -max_loss_on_assignment], # Trade
            [0, 0]                                      # Cash
        ])

        # 2. Calculate Regret Matrix
        # Regret = (Best possible outcome for that state) - (Actual outcome)
        best_per_state = np.max(utility_matrix, axis=0)
        regret_matrix = best_per_state - utility_matrix

        # 3. Incorporate Bayesian Probabilities (L3 Input)
        # Expected Regret = Regret * Probability
        expected_regret_trade = (regret_matrix[0, 0] * (1 - prob_assignment)) + \
                                (regret_matrix[0, 1] * prob_assignment)
        
        expected_regret_cash = (regret_matrix[1, 0] * (1 - prob_assignment)) + \
                               (regret_matrix[1, 1] * prob_assignment)

        # 4. Decision Logic
        decision = "EXECUTE" if expected_regret_trade < expected_regret_cash else "AVOID"
        
        return {
            "decision": decision,
            "regret_trade": round(expected_regret_trade, 2),
            "regret_cash": round(expected_regret_cash, 2),
            "confidence": round(abs(expected_regret_trade - expected_regret_cash), 2)
        }

    def evaluate_roll_opportunity(self, 
                                 current_p_assignment: float, 
                                 roll_credit: float, 
                                 new_p_assignment: float) -> bool:
        """
        Game theoretic decision to 'Roll' a position.
        """
        # Simple heuristic: If the Bayesian risk reduction outweighs the loss of time
        risk_reduction = current_p_assignment - new_p_assignment
        return risk_reduction > (1.0 - self.risk_appetite) and roll_credit >= 0

# --- Usage Example for Execution Edge ---
if __name__ == "__main__":
    citadel = RiskCitadel(risk_appetite=0.6)

    # Inputs from L3 Bayesian Engine & L1 Data
    bayesian_p_assignment = 0.72  # 72% chance of assignment from GraphFactory
    potential_premium = 150.0     # $150 credit
    worst_case_loss = 2500.0      # Potential drawdown if stock tanks

    result = citadel.calculate_minimax_decision(
        prob_assignment=bayesian_p_assignment,
        premium_capture=potential_premium,
        max_loss_on_assignment=worst_case_loss
    )

    print(f"--- Risk Citadel Decision Engine ---")
    print(f"Bayesian Risk: {bayesian_p_assignment*100}%")
    print(f"Decision: {result['decision']}")
    print(f"Trade Regret: {result['regret_trade']}")
    print(f"Cash Regret (Opportunity Cost): {result['regret_cash']}")
    
    if result['decision'] == "AVOID":
        print("Reason: Maximum potential regret from assignment outweighs premium capture.")