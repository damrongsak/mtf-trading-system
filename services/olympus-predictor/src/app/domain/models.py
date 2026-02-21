import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
import joblib
import os
import json
import logging
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Optional, Dict, List
from datetime import datetime, timezone
from hmmlearn.hmm import GaussianHMM
from statsmodels.tsa.vector_ar.var_model import VAR
from src.app.domain.features import FeatureEngine
from src.app.domain.transformers import LogReturnTransformer
from src.app.infrastructure.feature_store import FeatureStore
from src.app.infrastructure.data_loader import DataLoader

logger = logging.getLogger("olympus-predictor.domain.models")

class ResidualLSTM(nn.Module):
    """
    LSTM that predicts the residual of SARIMAX.
    Enhanced with Self-Attention and Distributional Head for Uncertainty.
    """
    def __init__(self, input_dim=1, hidden_dim=64, layer_dim=2, output_dim=2, dropout=0.3):
        super(ResidualLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.layer_dim = layer_dim
        
        self.lstm = nn.LSTM(input_dim, hidden_dim, layer_dim, batch_first=True, dropout=dropout if layer_dim > 1 else 0)
        
        # Scaled Dot-Product Attention
        self.query = nn.Linear(hidden_dim, hidden_dim)
        self.key = nn.Linear(hidden_dim, hidden_dim)
        self.value = nn.Linear(hidden_dim, hidden_dim)
        
        self.fc = nn.Linear(hidden_dim, output_dim) # Output: [mean, log_var]
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x shape: (batch, seq_len, input_dim)
        h0 = torch.zeros(self.layer_dim, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.layer_dim, x.size(0), self.hidden_dim).to(x.device)
        
        lstm_out, _ = self.lstm(x, (h0, c0)) # lstm_out: (batch, seq_len, hidden_dim)
        
        # Self-Attention Mechanism
        q = self.query(lstm_out)
        k = self.key(lstm_out)
        v = self.value(lstm_out)
        
        # attention weights: (batch, seq_len, seq_len)
        d_k = q.size(-1)
        scores = torch.matmul(q, k.transpose(-2, -1)) / (d_k ** 0.5)
        attn_weights = torch.softmax(scores, dim=-1)
        
        # context vector: (batch, seq_len, hidden_dim)
        context = torch.matmul(attn_weights, v)
        
        # Take the context of the last time step for prediction
        attended_out = context[:, -1, :]
        
        out = self.fc(self.dropout(attended_out))
        
        # Mean is unbounded, Std must be positive
        mean = out[:, 0:1]
        log_var = out[:, 1:2]
        std = torch.exp(0.5 * log_var)
        return mean, std

class MacroForecaster:
    """
    Sub-model to forecast exogenous macro inputs for multi-step prediction.
    Replaces naive last-value assumption.
    """
    def __init__(self, model_dir="/app/models"):
        self.model_dir = model_dir
        self.var_model = None
        self.var_path = os.path.join(model_dir, "macro_var.pkl")
        self.columns_path = os.path.join(model_dir, "macro_cols.pkl")
        self.columns = []

    def train(self, df: pd.DataFrame):
        """Train VAR model on macro features"""
        if df is None or df.empty or len(df) < 50: 
            logger.warning("Not enough macro data for VAR training. Fallback to Naive.")
            return
            
        self.columns = df.columns.tolist()
        try:
             # Train simple VAR(1) for speed and stability
             model = VAR(df)
             self.var_model = model.fit(maxlags=1)
             joblib.dump(self.var_model, self.var_path)
             joblib.dump(self.columns, self.columns_path)
             logger.info(f"MacroForecaster trained successfully on columns: {self.columns}")
        except Exception as e:
             logger.error(f"Failed to train Macro VAR: {e}")

    def load(self):
        if os.path.exists(self.var_path):
            try:
                self.var_model = joblib.load(self.var_path)
                self.columns = joblib.load(self.columns_path)
            except Exception as e:
                logger.error(f"Failed to load MacroForecaster: {e}")

    def forecast(self, steps=5, last_values: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Forecast future macro values"""
        if self.var_model is None or last_values is None or last_values.empty:
            if last_values is not None and not last_values.empty:
                logger.debug("Macro VAR not available, falling back to Naive forecast.")
                return pd.DataFrame([last_values.iloc[-1]] * steps, columns=last_values.columns)
            return pd.DataFrame()

        try:
            # Ensure we only use columns the model was trained on
            forecast_input = last_values[self.columns].values[-1:] 
            forecast_np = self.var_model.forecast(y=forecast_input, steps=steps)
            return pd.DataFrame(forecast_np, columns=self.columns)
        except Exception as e:
            logger.warning(f"Macro VAR forecasting failed: {e}. Falling back to Naive.")
            return pd.DataFrame([last_values.iloc[-1]] * steps, columns=last_values.columns)

class RegimeDetector:
    """
    HMM-based Market Regime detector (Trend/Range/Volatile).
    """
    def __init__(self, model_dir="/app/models", n_components=3):
        self.model_dir = model_dir
        self.n_components = n_components
        self.model = None
        self.path = os.path.join(model_dir, "regime_hmm.pkl")

    def train(self, df: pd.DataFrame):
        """Train HMM on Log-Returns and GARCH Volatility"""
        if df.empty or 'garch_vol' not in df.columns:
            return
            
        returns = np.log(df['close'] / df['close'].shift(1)).dropna()
        vol = df.loc[returns.index, 'garch_vol']
        X = np.column_stack([returns.values, vol.values])
        
        try:
            self.model = GaussianHMM(n_components=self.n_components, covariance_type="diag", n_iter=100)
            self.model.fit(X)
            joblib.dump(self.model, self.path)
            logger.info(f"RegimeDetector trained with {self.n_components} regimes.")
        except Exception as e:
            logger.error(f"RegimeDetector training failed: {e}")

    def load(self):
        if os.path.exists(self.path):
            self.model = joblib.load(self.path)

    def predict_regime(self, returns: float, vol: float) -> int:
        if self.model is None: return 0
        try:
            X = np.array([[returns, vol]])
            return int(self.model.predict(X)[0])
        except:
            return 0

class HybridPredictor:
    def __init__(self, model_dir="/app/models", feature_store: Optional["FeatureStore"] = None):
        self.model_dir = model_dir
        self.lookback = 60
        os.makedirs(model_dir, exist_ok=True)
        self.feature_store = feature_store
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Artifact paths (Symlinks to latest)
        self.sarimax_path = os.path.join(model_dir, "sarimax_xau.pkl")
        self.lstm_path = os.path.join(model_dir, "lstm_residual.pth")
        self.scaler_path = os.path.join(model_dir, "scaler.pkl")
        self.exog_scaler_path = os.path.join(model_dir, "exog_scaler.pkl")
        
        # Components
        self.feature_engine = FeatureEngine(model_dir, feature_store=feature_store)
        self.macro_forecaster = MacroForecaster(model_dir)
        self.regime_detector = RegimeDetector(model_dir)
        
        self.sarimax_model = None
        self.lstm_model = None
        self.scaler = None
        self.exog_scaler = None
        
        # Config
        self.exog_features = []

    def load_models(self):
        """Load trained artifacts"""
        if os.path.exists(self.sarimax_path):
            self.sarimax_model = joblib.load(self.sarimax_path)
        if os.path.exists(self.scaler_path):
            self.scaler = joblib.load(self.scaler_path)
        if os.path.exists(self.exog_scaler_path):
            self.exog_scaler = joblib.load(self.exog_scaler_path)
        
        self.feature_engine.load_selector()
        self.exog_features = self.feature_engine.selected_features
        
        self.macro_forecaster.load()
        self.regime_detector.load()
            
        if os.path.exists(self.lstm_path):
            # Input dim: Residual + Exog + Regime
            input_dim = 1 + len(self.exog_features) + 1
            self.lstm_model = ResidualLSTM(input_dim=input_dim).to(self.device)
            self.lstm_model.load_state_dict(torch.load(self.lstm_path, map_location=self.device))
            self.lstm_model.eval()

    async def train(self, df: pd.DataFrame, macro_df: Optional[pd.DataFrame] = None) -> dict:
        """Full Training Pipeline using Log-Returns"""
        logger.info("Starting Hybrid Training (Log-Returns)...")
        
        # 1. Transform Target to Log-Returns
        df_target = LogReturnTransformer.transform(df['close'])
        # Re-align original df to match transformer offset (t=1 onwards)
        df_aligned = df.loc[df_target.index]
        target_values = df_target.values
        
        # 2. Feature Engineering
        df_tech = await self.feature_engine.compute_technicals(df_aligned)
        df_tech = df_tech.dropna()
        
        # 3. Sentiment Data (Phase 4)
        loader = DataLoader(None, self.feature_store.redis if self.feature_store else None)
        df_sent = await loader.get_sentiment_data(symbol='XAUUSD', lookback_days=30)
        
        common_idx = df_target.index.intersection(df_tech.index)
        if macro_df is not None and not macro_df.empty:
            common_idx = common_idx.intersection(macro_df.index)
            
        if not df_sent.empty:
            common_idx = common_idx.intersection(df_sent.index)
            
        if common_idx.empty:
             logger.warning("No overlapping index found between Gold, Technicals, Macro, and Sentiment. Falling back to alignment path.")
             common_idx = df_target.index.intersection(df_tech.index).dropna()
             macro_df = None 
             df_sent = pd.DataFrame(0.0, index=common_idx, columns=['score']) # Full Neutral Fallback
             
        y_train = df_target.loc[common_idx]
        X_tech = df_tech.loc[common_idx]
        
        # Merge technicals, macro, and sentiment
        tech_cols = ['stoch_k', 'stoch_d', 'stoch_d_smooth', 'williams_r', 'rsi', 'macd', 'macd_signal', 'atr', 'ema_5', 'ema_10', 'garch_vol']
        tech_cols = [c for c in tech_cols if c in X_tech.columns]
        
        combined_features = X_tech[tech_cols]
        if macro_df is not None:
            combined_features = combined_features.join(macro_df.loc[common_idx], rsuffix='_macro')
        
        if not df_sent.empty:
             # Align sentiment by forward filling (sentiment is often lower frequency)
             sent_aligned = df_sent.reindex(common_idx).ffill().fillna(0.0)
             combined_features['sentiment'] = sent_aligned['score']
        else:
             combined_features['sentiment'] = 0.0
             
        # 4. Feature Selection
        if not combined_features.empty:
            self.feature_engine.select_features(combined_features, y_train)
            self.exog_features = self.feature_engine.selected_features
            selected_exog = combined_features[self.exog_features]
        else:
            selected_exog = pd.DataFrame()

        # 4. SARIMAX on Log-Returns
        order = (1, 1, 1)
        logger.info(f"Training SARIMAX{order} on Log-Returns (N={len(y_train)})...")
        sarimax = SARIMAX(y_train.values, order=order, enforce_stationarity=False)
        self.sarimax_model = sarimax.fit(disp=False)
        joblib.dump(self.sarimax_model, self.sarimax_path)
        
        # 5. Extract Residuals
        linear_pred = self.sarimax_model.fittedvalues
        residuals = y_train.values - linear_pred
        logger.info(f"Residuals extracted. Shape: {residuals.shape}")
        
        if len(residuals) == 0:
             raise ValueError("Residuals are empty after SARIMAX fit.")

        # 6. Preprocess for LSTM
        scaler = MinMaxScaler(feature_range=(-1, 1))
        residuals_scaled = scaler.fit_transform(residuals.reshape(-1, 1))
        self.scaler = scaler
        joblib.dump(self.scaler, self.scaler_path)
        
        # NEW Phase 2: Macro Forecasting & Regime Awareness during training
        # We'll calculate regimes for all training samples to use as features
        returns = np.log(df_aligned['close'] / df_aligned['close'].shift(1)).fillna(0)
        self.regime_detector.train(df_aligned)
        
        regimes = []
        for r, v in zip(returns.loc[common_idx].values, df_tech.loc[common_idx, 'garch_vol'].values):
            regimes.append(self.regime_detector.predict_regime(r, v))
        
        # Convert regimes to categorical/one-hot or just a scaled feature? 
        # For simplicity in this upgrade, let's treat it as a scaled feature [0, 1]
        regimes_scaled = np.array(regimes).reshape(-1, 1) / (self.regime_detector.n_components - 1)
        
        if not selected_exog.empty:
            self.macro_forecaster.train(macro_df) # Train dynamic macro forecaster
            
            self.exog_scaler = MinMaxScaler(feature_range=(-1, 1))
            exog_scaled = self.exog_scaler.fit_transform(selected_exog.values)
            joblib.dump(self.exog_scaler, self.exog_scaler_path)
            # Input = [Residual, Exog..., Regime]
            lstm_input_data = np.hstack([residuals_scaled, exog_scaled, regimes_scaled])
        else:
            lstm_input_data = np.hstack([residuals_scaled, regimes_scaled])
            
        input_dim = lstm_input_data.shape[1]
        X, y = self._create_sequences(lstm_input_data, self.lookback)
        y = y[:, 0] # Residual is target
        
        X_tensor = torch.from_numpy(X).float().to(self.device)
        y_tensor = torch.from_numpy(y).float().to(self.device)
        
        # 7. Train Residual LSTM (Distributional + Attention)
        self.lstm_model = ResidualLSTM(input_dim=input_dim).to(self.device)
        # NLL Loss for Gaussian Uncertainty + Risk-Adjusted Penalty (Phase 4)
        def risk_adjusted_loss(mean, std, target, alpha=0.1):
            nll = 0.5 * torch.mean(torch.log(std**2) + (target - mean)**2 / std**2)
            # Penalty for "Regret": high loss if predicted direction is wrong AND actual return is large
            # Directional alignment penalty
            regret = torch.mean(torch.relu(-target * mean)) 
            return nll + alpha * regret
            
        optimizer = torch.optim.Adam(self.lstm_model.parameters(), lr=0.001)
        epochs = 50
        self.lstm_model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            mean, std = self.lstm_model(X_tensor)
            loss = risk_adjusted_loss(mean, std, y_tensor.unsqueeze(1))
            loss.backward()
            optimizer.step()
            
            if (epoch+1) % 10 == 0:
                logger.debug(f"Epoch [{epoch+1}/{epochs}], NLL Loss: {loss.item():.6f}")
                
        # Save latest
        torch.save(self.lstm_model.state_dict(), self.lstm_path)
        
        # Phase 3: Archive version
        await self.save_versioned_model(loss.item())
        
        return {"status": "success", "final_loss": loss.item(), "selected_features": self.exog_features}

    async def save_versioned_model(self, metric: float):
        """Save a versioned snapshot of the current models"""
        try:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            v_dir = os.path.join(self.model_dir, "versions", f"v_{version}")
            os.makedirs(v_dir, exist_ok=True)
            
            logger.info(f"Archiving model version {version}...")
            
            # Save artifacts to versioned dir
            if self.sarimax_model:
                joblib.dump(self.sarimax_model, os.path.join(v_dir, "sarimax_xau.pkl"))
            if self.scaler:
                joblib.dump(self.scaler, os.path.join(v_dir, "scaler.pkl"))
            if self.exog_scaler:
                joblib.dump(self.exog_scaler, os.path.join(v_dir, "exog_scaler.pkl"))
            if self.lstm_model:
                torch.save(self.lstm_model.state_dict(), os.path.join(v_dir, "lstm_residual.pth"))
            
            # Save metadata
            metadata = {
                "version": version,
                "metric_nll_loss": metric,
                "features": self.exog_features,
                "timestamp": datetime.now().isoformat()
            }
            with open(os.path.join(v_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f)
            
            logger.info(f"Model version {version} archived successfully.")
        except Exception as e:
            logger.error(f"Failed to archive model version: {e}")

    async def predict(self, steps=5, macro_df: Optional[pd.DataFrame] = None, last_price: float = 0.0) -> dict:
        """Hybrid Inference: Returns Absolute Prices + Sigma"""
        if not self.sarimax_model or not self.lstm_model:
            self.load_models()
            if not self.sarimax_model:
                raise ValueError("Models not trained yet")

        # 1. Linear Forecast (Log-Returns)
        linear_forecast_lr = self.sarimax_model.forecast(steps=steps)
        
        # 2. Residual Forecast (Log-Returns)
        recent_residuals = self.sarimax_model.resid[-self.lookback:]
        recent_scaled = self.scaler.transform(recent_residuals.reshape(-1, 1))
        
        # NEW Phase 4: Fetch Latest Sentiment
        loader = DataLoader(None, self.feature_store.redis if self.feature_store else None)
        df_sent = await loader.get_sentiment_data(symbol='XAUUSD', lookback_days=1)
        latest_sentiment = df_sent['score'].iloc[-1] if not df_sent.empty else 0.0
        
        if self.exog_features and macro_df is not None:
             macro_forecast_df = self.macro_forecaster.forecast(steps=steps, last_values=macro_df)
             
             # Prep history for sequence window
             available_f = [f for f in self.exog_features if f in macro_df.columns]
             missing_f = [f for f in self.exog_features if f not in macro_df.columns]
             
             exog_history_df = macro_df[available_f].tail(self.lookback).copy()
             for f in missing_f: exog_history_df[f] = 0
             
             # Add sentiment to exog history if it was selected
             if 'sentiment' in self.exog_features:
                  exog_history_df['sentiment'] = latest_sentiment # Assume static sentiment for history window if not available
             
             exog_history = exog_history_df[self.exog_features].values
             exog_scaled_history = self.exog_scaler.transform(exog_history)
             
             current_regime = 0
             
             lstm_input_np = np.hstack([recent_scaled, exog_scaled_history, np.full((self.lookback, 1), current_regime/2.0)])
        else:
             # No exog selected? Boruta might have picked only technicals
             lstm_input_np = np.hstack([recent_scaled, np.full((self.lookback, 1), current_regime/2.0)])
 
        curr_input = torch.from_numpy(lstm_input_np).float().view(1, self.lookback, -1).to(self.device)
        
        residual_means = []
        residual_stds = []
        self.lstm_model.eval()
        
        with torch.no_grad():
            for i in range(steps):
                mean, std = self.lstm_model(curr_input)
                residual_means.append(mean.item())
                residual_stds.append(std.item())
                
                # Iterative update with Dynamic Macro
                new_residual_scaled = mean.view(1, 1, 1)
                
                if not macro_forecast_df.empty:
                    exog_step_df = macro_forecast_df.iloc[i:i+1].copy()
                    
                    for f in self.exog_features:
                        if f not in exog_step_df.columns:
                            if f == 'sentiment':
                                 exog_step_df[f] = latest_sentiment
                            else:
                                 exog_step_df[f] = 0 
                            
                    exog_step_scaled = self.exog_scaler.transform(exog_step_df[self.exog_features].values)
                    new_exog = torch.from_numpy(exog_step_scaled).float().to(self.device).unsqueeze(0)
                    
                    new_regime = torch.full((1, 1, 1), current_regime/2.0).to(self.device)
                    new_step = torch.cat([new_residual_scaled, new_exog, new_regime], dim=2)
                else:
                    new_regime = torch.full((1, 1, 1), current_regime/2.0).to(self.device)
                    new_step = torch.cat([new_residual_scaled, new_regime], dim=2)
                
                curr_input = torch.cat((curr_input[:, 1:, :], new_step), dim=1)
                
        # Inverse Scale Residual Mean
        res_means_scaled = np.array(residual_means).reshape(-1, 1)
        res_final_lr = self.scaler.inverse_transform(res_means_scaled).flatten()
        
        # 3. Combine in Log-Return Space
        total_lr = linear_forecast_lr + res_final_lr
        
        # 4. Convert back to Absolute Prices
        if last_price == 0:
             logger.warning("last_price not provided to predict. Values will be relative only.")
             prices = np.exp(np.cumsum(total_lr)) # Factors
        else:
             prices = LogReturnTransformer.inverse_transform(last_price, total_lr)
             
        # Uncertainty is approximated in return space (simplified)
        sigma_lr = np.array(residual_stds)
        
        return {
            "prices": prices.tolist(),
            "log_returns": total_lr.tolist(),
            "sigma_lr": sigma_lr.tolist(),
            "sentiment": float(latest_sentiment)
        }

    async def generate_signal(self, prediction: dict, threshold=0.002) -> dict:
        """
        Phase 4: Convert raw prediction into a Confidence-Weighted Signal.
        Optimized for Strategy Alignment.
        """
        prices = prediction["prices"]
        sigma = prediction["sigma_lr"]
        sentiment = prediction["sentiment"]
        
        expected_return = (prices[-1] / prices[0]) - 1
        avg_vol = np.mean(sigma)
        
        # Confidence = Return / Volatility (Risk-adjusted confidence)
        confidence = min(max(abs(expected_return) / (avg_vol * 3), 0), 1)
        
        direction = "BUY" if expected_return > threshold else "SELL" if expected_return < -threshold else "NEUTRAL"
        
        # institutional Grade Audit
        await self.log_signal_audit(direction, confidence, prediction)
        
        return {
            "direction": direction,
            "target": prices[-1],
            "stop_loss": prices[0] * (1 - (2 * avg_vol) if direction == "BUY" else 1 + (2 * avg_vol)),
            "confidence": confidence,
            "sentiment_score": sentiment
        }

    async def log_signal_audit(self, direction: str, confidence: float, context: dict):
        """Traceability: Log the prediction context for audit."""
        try:
             # In a real system, this would write to the `signal_logs` table
             # Here we use logger for demonstration, but the pattern is established
             audit_entry = {
                 "timestamp": datetime.now().isoformat(),
                 "direction": direction,
                 "confidence": confidence,
                 "model_version": getattr(self, 'current_version', 'latest'),
                 "sentiment": context.get("sentiment"),
                 "expected_price": context["prices"][-1]
             }
             logger.info(f"AUDIT_SIGNAL: {json.dumps(audit_entry)}")
        except Exception as e:
             logger.error(f"Audit logging failed: {e}")

    def _create_sequences(self, data, lookback):
        X, y = [], []
        for i in range(len(data) - lookback):
            X.append(data[i:(i + lookback)])
            y.append(data[i + lookback])
        return np.array(X), np.array(y)
