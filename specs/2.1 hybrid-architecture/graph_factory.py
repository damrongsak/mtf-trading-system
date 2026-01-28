import json
import pandas as pd
from typing import Dict, List, Any
from pgmpy.models import BayesianNetwork
from pgmpy.factors.discrete import TabularCPD
from pgmpy.estimators import MaximumLikelihoodEstimator, BayesianEstimator

class GraphFactory:
    """
    MTF Olympus - L2/L3 Hybrid Layer
    Converts LLM-generated JSON DAGs into runnable Bayesian Networks.
    """

    def __init__(self, historical_data: pd.DataFrame):
        """
        :param historical_data: A DataFrame from L1 (Data Pipeline) tagged by regime.
                                Should be pre-discretized (binned) into states.
        """
        self.data = historical_data

    def create_model(self, dag_json: str) -> BayesianNetwork:
        """
        Parses LLM output and builds the network structure.
        """
        spec = json.loads(dag_json)
        edges = [(edge['from'], edge['to']) for edge in spec['edges']]
        
        # Initialize the Bayesian Network structure
        model = BayesianNetwork(edges)
        
        print(f"Constructed Model for Regime: {spec.get('regime_id')}")
        return model

    def calibrate_model(self, model: BayesianNetwork, method: str = 'BDeu') -> BayesianNetwork:
        """
        L3 Proving Ground: Populates CPTs using historical data.
        Uses Bayesian Estimation to handle 'Zero-frequency' problems (Laplace Smoothing).
        """
        # Fit the model using historical data
        # 'BDeu' is a common prior for Bayesian parameter estimation
        if method == 'MLE':
            model.fit(self.data, estimator=MaximumLikelihoodEstimator)
        else:
            model.fit(self.data, estimator=BayesianEstimator, prior_type="BDeu")
            
        # Validate that the model is consistent
        if model.check_model():
            print("Model calibration successful and consistent.")
        
        return model

    def get_inference_query(self, model: BayesianNetwork, target: str, evidence: Dict[str, Any]):
        """
        Executes a query to find the probability of an outcome given current evidence.
        Example: target='Assignment_Risk', evidence={'VIX_Trend': 'RISING', 'Price_Action': 'STABLE'}
        """
        from pgmpy.inference import VariableElimination
        
        infer = VariableElimination(model)
        result = infer.query(variables=[target], evidence=evidence)
        
        return result

# --- Usage Example for Strategy Core ---
if __name__ == "__main__":
    # 1. Mock Data from L1 (Data Pipeline) - Variables must match LLM node states
    # In production, this is pulled via Redis/Postgres filtered by 'Regime'
    mock_l1_data = pd.DataFrame({
        "VIX_Trend": ["RISING", "FALLING", "RISING", "STABLE"] * 25,
        "Market_Regime": ["BEAR", "BULL", "BEAR", "NEUTRAL"] * 25,
        "Assignment_Risk": ["HIGH", "LOW", "HIGH", "LOW"] * 25
    })

    # 2. Mock JSON from L5 AI-Analyst (The Architect)
    llm_output = """
    {
      "regime_id": "volatile_bear_recovery",
      "nodes": [
        {"id": "VIX_Trend", "type": "technical", "states": ["RISING", "STABLE", "FALLING"]},
        {"id": "Market_Regime", "type": "context", "states": ["BEAR", "BULL", "NEUTRAL"]},
        {"id": "Assignment_Risk", "type": "target", "states": ["LOW", "MEDIUM", "HIGH"]}
      ],
      "edges": [
        {"from": "Market_Regime", "to": "VIX_Trend"},
        {"from": "VIX_Trend", "to": "Assignment_Risk"}
      ]
    }
    """

    factory = GraphFactory(mock_l1_data)
    
    # Create structure (L2)
    olympus_model = factory.create_model(llm_output)
    
    # Calibrate parameters (L3)
    calibrated_model = factory.calibrate_model(olympus_model)
    
    # Query for decision making (L4 Risk Citadel input)
    current_evidence = {"VIX_Trend": "RISING", "Market_Regime": "BEAR"}
    prob_dist = factory.get_inference_query(calibrated_model, "Assignment_Risk", current_evidence)
    
    print("\nInference Result (Assignment_Risk Distribution):")
    print(prob_dist)