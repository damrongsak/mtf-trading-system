import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from boruta import BorutaPy
import shap
import logging
import joblib
import os

logger = logging.getLogger("olympus-predictor.features")

class FeatureEngine:
    def __init__(self, model_dir="/app/models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.selector_path = os.path.join(model_dir, "boruta_selector.pkl")
        self.selected_features = []
        
    def load_selector(self):
        if os.path.exists(self.selector_path):
            state = joblib.load(self.selector_path)
            self.selected_features = state.get('selected_features', [])
            logger.info(f"Loaded feature selector with {len(self.selected_features)} features: {self.selected_features}")
            
    def select_features(self, X: pd.DataFrame, y: pd.Series) -> list:
        """
        Select important features using Boruta-SHAP approach.
        We use BorutaPy with Random Forest as it's robust.
        SHAP values can be used for explanation later.
        """
        logger.info(f"Starting Feature Selection on {X.shape[1]} features...")
        
        # Initialize Random Forest
        rf = RandomForestRegressor(n_jobs=-1, max_depth=5)
        
        # Initialize Boruta
        feat_selector = BorutaPy(
            rf, 
            n_estimators='auto', 
            verbose=0, 
            random_state=42,
            max_iter=50 # limit iterations for speed in this MVP
        )
        
        # Fit Boruta
        # BorutaPy accepts numpy arrays
        feat_selector.fit(X.values, y.values)
        
        # Get selected features
        selected_mask = feat_selector.support_
        selected_features = X.columns[selected_mask].tolist()
        
        # Fallback if no features selected (rare but possible)
        if not selected_features:
            logger.warning("Boruta selected 0 features! Falling back to top 5 correlations.")
            corrs = X.corrwith(y).abs().sort_values(ascending=False)
            selected_features = corrs.head(5).index.tolist()
            
        self.selected_features = selected_features
        logger.info(f"Boruta selected {len(selected_features)} features: {selected_features}")
        
        # Save state
        joblib.dump({'selected_features': selected_features}, self.selector_path)
        
        return selected_features
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Filter X to only selected features"""
        if not self.selected_features:
             self.load_selector()
             if not self.selected_features:
                 # If still empty, return original (or raise error?)
                 # For robustness, return original if nothing saved yet (e.g. inference before training? shouldn't happen)
                 return X
        
        # Ensure all selected features exist in X
        # If missing, fill with 0 or drop? 
        # Better to fail if critical features missing
        missing = [f for f in self.selected_features if f not in X.columns]
        if missing:
            logger.warning(f"Missing features in input: {missing}")
            # Add missing columns with 0
            for m in missing:
                X[m] = 0
                
        return X[self.selected_features]
