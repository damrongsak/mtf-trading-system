import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from boruta import BorutaPy
import logging
import joblib
import os

logger = logging.getLogger("olympus-predictor.domain.features")

try:
    from arch import arch_model
except ImportError:
    logger.warning("arch package not found. GARCH features will be disabled.")
    arch_model = None

class FeatureEngine:
    def __init__(self, model_dir="/app/models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.selector_path = os.path.join(model_dir, "boruta_selector.pkl")
        self.selected_features = []
        
    def compute_technicals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute SOTA technical indicators
        - Stoch, Williams, RSI, MACD, ATR, EMA(5,10)
        - GARCH(1,1) Volatility
        """
        df = df.copy()
        
        # 1. Stochastic Oscillator (9, 3, 3)
        n = 9
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()
        df['stoch_k'] = 100 * ((df['close'] - low_n) / (high_n - low_n))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        df['stoch_d_smooth'] = df['stoch_d'].rolling(window=3).mean()
        
        # 2. Williams %R (14)
        n = 14
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()
        df['williams_r'] = -100 * ((high_n - df['close']) / (high_n - low_n))
        
        # 3. RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 4. MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # 5. ATR (14)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # 6. EMA (5, 10)
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
        
        # 7. GARCH(1,1) Volatility
        if arch_model:
            returns = 100 * df['close'].pct_change()
            try:
                am = arch_model(returns.dropna(), vol='Garch', p=1, o=0, q=1, dist='Normal')
                res = am.fit(disp='off')
                df.loc[returns.index, 'garch_vol'] = res.conditional_volatility
            except Exception as e:
                logger.warning(f"GARCH calc failed: {e}")
                df['garch_vol'] = 0
        
        return df

    def load_selector(self):
        if os.path.exists(self.selector_path):
            state = joblib.load(self.selector_path)
            self.selected_features = state.get('selected_features', [])
            logger.info(f"Loaded feature selector with {len(self.selected_features)} features")
            
    def select_features(self, X: pd.DataFrame, y: pd.Series) -> list:
        """Select important features using Boruta"""
        logger.info(f"Starting Feature Selection on {X.shape[1]} features...")
        rf = RandomForestRegressor(n_jobs=-1, max_depth=5)
        feat_selector = BorutaPy(rf, n_estimators='auto', verbose=0, random_state=42, max_iter=50)
        feat_selector.fit(X.values, y.values)
        
        selected_features = X.columns[feat_selector.support_].tolist()
        if not selected_features:
            logger.warning("Boruta selected 0 features! Falling back to top 5 correlations.")
            corrs = X.corrwith(y).abs().sort_values(ascending=False)
            selected_features = corrs.head(5).index.tolist()
            
        self.selected_features = selected_features
        joblib.dump({'selected_features': selected_features}, self.selector_path)
        return selected_features
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Filter X to only selected features"""
        if not self.selected_features:
             self.load_selector()
             if not self.selected_features:
                  return X
        
        missing = [f for f in self.selected_features if f not in X.columns]
        if missing:
            for m in missing:
                X[m] = 0
        return X[self.selected_features]
