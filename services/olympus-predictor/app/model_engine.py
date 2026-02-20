import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
import joblib
import os
import logging
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple

logger = logging.getLogger("olympus-predictor.engine")

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
import joblib
import os
import logging
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Optional
from app.feature_engine import FeatureEngine

logger = logging.getLogger("olympus-predictor.engine")

class ResidualLSTM(nn.Module):
    def __init__(self, input_dim=1, hidden_dim=50, layer_dim=1, output_dim=1, dropout=0.3):
        super(ResidualLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.layer_dim = layer_dim
        self.lstm = nn.LSTM(input_dim, hidden_dim, layer_dim, batch_first=True, dropout=dropout if layer_dim > 1 else 0)
        self.fc = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        h0 = torch.zeros(self.layer_dim, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.layer_dim, x.size(0), self.hidden_dim).to(x.device)
        out, (hn, cn) = self.lstm(x, (h0, c0))
        out = self.fc(self.dropout(out[:, -1, :]))
        return out

class HybridPredictor:
    def __init__(self, model_dir="/app/models"):
        self.model_dir = model_dir
        self.lookback = 60 # Increased sequence length for real data
        os.makedirs(model_dir, exist_ok=True)
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Artifact paths
        self.sarimax_path = os.path.join(model_dir, "sarimax_xau.pkl")
        self.lstm_path = os.path.join(model_dir, "lstm_residual.pth")
        self.scaler_path = os.path.join(model_dir, "scaler.pkl")
        
        # Components
        self.feature_engine = FeatureEngine(model_dir)
        self.exog_scaler_path = os.path.join(model_dir, "exog_scaler.pkl")
        self.sarimax_model = None
        self.lstm_model = None
        self.scaler = None
        self.exog_scaler = None
        
        # Config
        self.exog_features = [] # List of selected feature names

    def load_models(self):
        """Load trained artifacts"""
        if os.path.exists(self.sarimax_path):
            self.sarimax_model = joblib.load(self.sarimax_path)
            
        if os.path.exists(self.scaler_path):
            self.scaler = joblib.load(self.scaler_path)
            
        if os.path.exists(self.exog_scaler_path):
            self.exog_scaler = joblib.load(self.exog_scaler_path)
        
        # Load feature selector state
        self.feature_engine.load_selector()
        self.exog_features = self.feature_engine.selected_features
            
        if os.path.exists(self.lstm_path):
            # Input dim = 1 (residual) + len(exog_features)
            input_dim = 1 + len(self.exog_features)
            self.lstm_model = ResidualLSTM(input_dim=input_dim).to(self.device)
            self.lstm_model.load_state_dict(torch.load(self.lstm_path, map_location=self.device))
            self.lstm_model.eval()

    def train(self, df: pd.DataFrame, macro_df: Optional[pd.DataFrame] = None) -> dict:
        """
        Full Training Pipeline:
        1. Select Features from macro_df using Boruta (if provided).
        2. Train SARIMAX on Close price (with exog if linear, but usually we keep SARIMAX univariate and put exog in LSTM for non-linear).
           Paper approach: "Selected variables... entered as inputs to Neural Network".
           So SARIMAX handles linear autocorrelation of price. LSTM handles Residuals + Exogenous features.
        3. Calculate Residuals.
        4. Train LSTM on Residuals + Selected Macro Features.
        """
        logger.info("Starting Hybrid Training...")
        target = df['close'].values
        
        # 0. Feature Engineering (Technicals + GARCH)
        # This matches paper_experiments.py logic
        df_tech = self.feature_engine.compute_technicals(df)
        
        # Align indexes
        # Drop NaN caused by technicals
        df_tech = df_tech.dropna()
        common_idx = df.index.intersection(df_tech.index)
        if macro_df is not None:
            common_idx = common_idx.intersection(macro_df.index)
        
        df = df.loc[common_idx]
        if macro_df is not None:
             macro_df = macro_df.loc[common_idx]
        
        # Merge technicals into macro_df for selection
        # Identify technical columns (newly added)
        tech_cols = ['stoch_k', 'stoch_d', 'stoch_d_smooth', 'williams_r', 'rsi', 'macd', 'macd_signal', 'atr', 'ema_5', 'ema_10', 'garch_vol']
        # Filter only existing
        tech_cols = [c for c in tech_cols if c in df_tech.columns]
        
        if macro_df is None:
            combined_features = df_tech[tech_cols]
        else:
            combined_features = macro_df.join(df_tech[tech_cols])
            
        target = df['close'].values
        
        # Feature Selection
        selected_exog = pd.DataFrame()
        if not combined_features.empty:
            # Align macro data with target
            # Ensure index alignment
            common_idx = df.index.intersection(macro_df.index)
            if len(common_idx) < 50:
                logger.warning("Not enough overlapping data for Macro features. Skipping exog.")
            else:
                y_aligned = df['close']
                X_aligned = combined_features
                
                # Run Boruta
                self.feature_engine.select_features(X_aligned, y_aligned)
                self.exog_features = self.feature_engine.selected_features
                
                # Prepare aligned features for full dataset
                # We need to reindex macro_df to df.index, ffilling
                selected_exog = combined_features[self.exog_features].reindex(df.index).ffill().bfill()
        
        # 1. SARIMAX (Univariate for Price Trend)
        order = (1, 1, 1)
        seasonal_order = (0, 0, 0, 0)
        
        logger.info(f"Training SARIMAX{order}...")
        sarimax = SARIMAX(target, order=order, seasonal_order=seasonal_order, enforce_stationarity=False)
        self.sarimax_model = sarimax.fit(disp=False)
        joblib.dump(self.sarimax_model, self.sarimax_path)
        
        # 2. Extract Residuals
        linear_pred = self.sarimax_model.fittedvalues
        residuals = target - linear_pred
        
        # 3. Preprocess Inputs for LSTM
        # Input = Scaled Residuals + Scaled Exog Features
        scaler = MinMaxScaler(feature_range=(-1, 1))
        residuals_scaled = scaler.fit_transform(residuals.reshape(-1, 1))
        self.scaler = scaler
        joblib.dump(self.scaler, self.scaler_path)
        
        # Combine with Exog
        if not selected_exog.empty:
            # Scale exog features too? Yes, crucial for LSTM
            # We need a separate scaler for exog or scale together
            # For simplicity using MinMax on exog columns
            exog_values = selected_exog.values
            self.exog_scaler = MinMaxScaler(feature_range=(-1, 1))
            exog_scaled = self.exog_scaler.fit_transform(exog_values)
            joblib.dump(self.exog_scaler, self.exog_scaler_path)
            
            # Persist exog scaler? 
            # Yes, now we do.
            # OR just assume inputs are reasonably scaled roughly. 
            # Let's simple concat for now to demonstrate architecture
            lstm_input_data = np.hstack([residuals_scaled, exog_scaled])
        else:
            lstm_input_data = residuals_scaled
            
        input_dim = lstm_input_data.shape[1]
        
        # Create sequences
        X, y = self._create_sequences(lstm_input_data, self.lookback)
        # Target y is strictly the residual (column 0)
        # Wait, if we predict residual, y should be residual[t+1]
        # _create_sequences logic needs to know which column is target
        y = y[:, 0] # 0-th column is residuals
        
        X_tensor = torch.from_numpy(X).float().to(self.device)
        y_tensor = torch.from_numpy(y).float().to(self.device)
        
        # 4. Train LSTM
        logger.info(f"Training Residual LSTM (Input Dim: {input_dim})...")
        self.lstm_model = ResidualLSTM(input_dim=input_dim).to(self.device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.lstm_model.parameters(), lr=0.001)
        
        epochs = 50 
        self.lstm_model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.lstm_model(X_tensor)
            loss = criterion(outputs, y_tensor.unsqueeze(1)) # y needs shape (batch, 1) to match output
            loss.backward()
            optimizer.step()
            
            if (epoch+1) % 10 == 0:
                logger.info(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.6f}")
                
        # Save LSTM
        torch.save(self.lstm_model.state_dict(), self.lstm_path)
        
        return {"status": "success", "final_loss": loss.item(), "selected_features": self.exog_features}

    def predict(self, steps=5, macro_df: Optional[pd.DataFrame] = None) -> dict:
        """
        Hybrid Inference:
        1. Forecast Linear component
        2. Forecast Residual component iteratively (using macro features if available)
        3. Combine
        """
        if not self.sarimax_model or not self.lstm_model:
            self.load_models()
            if not self.sarimax_model:
                raise ValueError("Models not trained yet")

        # 1. Linear Forecast
        linear_forecast = self.sarimax_model.forecast(steps=steps)
        
        # 1.5 Calculate Technicals for Inference Context
        # We need the recent history to compute technicals (e.g. RSI 14 needs 14 candles)
        # Ideally, df passed to predict should have enough history.
        # If macro_df is passed, we assume it matches the steps? 
        # Actually, predict is usually called with recent market data context.
        # BUT here, the signature is predict(steps, macro_df). feature_engine needs PRICE data to compute technicals.
        # This implies we need access to recent price history here.
        # The SARIMAX model stores history? self.sarimax_model.data.endog ?
        # Yes, but that's training data.
        # For production inference, the Caller (API) should pass the recent 'df' context.
        # Current API design: POST /predict payload has 'prices'. 
        # Let's assume we can't compute dynamic technicals easily in this pure 'predict' method without the context df.
        # HOWEVER, the `train` method used `feature_engine.compute_technicals`.
        # If we selected 'rsi', we need 'rsi' for inference.
        # The `macro_df` argument MUST include these technicals if they were selected.
        # START MODIFICATION:
        # We assume `macro_df` passed to predict ALREADY contains the computed technicals (computed by the API handler from the input candles).
        # So we just need to ensure we pick them up.
        
        # 2. Residual Forecast
        # Prepare input: last 'lookback' residuals + exog features
        recent_residuals = self.sarimax_model.resid[-self.lookback:]
        recent_scaled = self.scaler.transform(recent_residuals.reshape(-1, 1))
        
        # Macro features for inference
        # In real prod, we need the LATEST macro values. 
        # If exog features were used, input dim must match.
        # Construct inference input vector
        if self.exog_features:
            # We need recent exog values corresponding to the lookback window
            # Simplification: Use provided macro_df tail or 0s if missing
            if macro_df is not None and not macro_df.empty:
                 # Align columns
                 # Check if we have all needed features
                 missing = [f for f in self.exog_features if f not in macro_df.columns]
                 if missing:
                     logger.warning(f"Inference missing features: {missing}. Filling with 0.")
                     for m in missing:
                         macro_df[m] = 0
                 
                 # Access features
                 exog_tail = macro_df[self.exog_features].tail(self.lookback).values
                 # Load persistent scaler
                 if not self.exog_scaler and os.path.exists(self.exog_scaler_path):
                     try:
                         self.exog_scaler = joblib.load(self.exog_scaler_path)
                     except Exception as e:
                         logger.warning(f"Failed to load exog_scaler: {e}")

                 if self.exog_scaler:
                     exog_scaled = self.exog_scaler.transform(exog_tail)
                 else:
                     logger.warning("No ExogScaler found. Fitting new one (Inference skew risk!)")
                     exog_scaler = MinMaxScaler(feature_range=(-1, 1))
                     exog_scaled = exog_scaler.fit_transform(exog_tail)

                 lstm_input_np = np.hstack([recent_scaled, exog_scaled])
            else:
                 # Fallback to Zeros for exog if missing
                 logger.warning("Macro data missing for inference, using zeros for exog features")
                 zeros = np.zeros((self.lookback, len(self.exog_features)))
                 lstm_input_np = np.hstack([recent_scaled, zeros])
        else:
            lstm_input_np = recent_scaled

        lstm_input = torch.from_numpy(lstm_input_np).float().view(1, self.lookback, -1).to(self.device)
        
        residual_forecasts = []
        self.lstm_model.eval()
        
        # For iterative forecast, we also need FUTURE exog values (or assume const/last known)
        # We will use last known exog for steps ahead (Naive assumption for MVP)
        last_exog = lstm_input[:, -1, 1:] # Shape (1, n_exog)
        
        with torch.no_grad():
            curr_input = lstm_input
            for _ in range(steps):
                pred = self.lstm_model(curr_input)
                residual_forecasts.append(pred.item())
                
                # Update input window
                # Shift left
                # Append new: [pred, last_exog]
                new_residual = pred.view(1, 1, 1)
                
                if self.exog_features:
                    # Append exog features (repeating last known)
                    new_step = torch.cat([new_residual, last_exog.unsqueeze(1)], dim=2)
                else:
                    new_step = new_residual
                    
                curr_input = torch.cat((curr_input[:, 1:, :], new_step), dim=1)
                
        # Inverse scale residuals
        residual_forecasts = np.array(residual_forecasts).reshape(-1, 1)
        residual_final = self.scaler.inverse_transform(residual_forecasts).flatten()
        
        # 3. Combine
        final_forecast = linear_forecast + residual_final
        
        return {
            "linear": linear_forecast.tolist(),
            "residual": residual_final.tolist(),
            "total": final_forecast.tolist(),
            "used_features": self.exog_features
        }

    def _create_sequences(self, data, lookback):
        X, y = [], []
        for i in range(len(data) - lookback):
            X.append(data[i:(i + lookback)])
            y.append(data[i + lookback])
        return np.array(X), np.array(y)
