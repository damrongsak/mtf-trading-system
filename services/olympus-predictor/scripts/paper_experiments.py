
import asyncio
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf
import asyncpg
import redis.asyncio as redis
from datetime import datetime, timedelta
from app.model_engine import HybridPredictor
from app.data_loader import DataLoader
import logging
import os
import joblib
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score
import torch
import torch.nn as nn
from statsmodels.tsa.statespace.sarimax import SARIMAX
from arch import arch_model  # Phase 3: GARCH
from sklearn.preprocessing import MinMaxScaler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paper_experiments")

RESULTS_DIR = "paper_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

async def fetch_data(use_synthetic=False):
    """Fetch real data using the service's DataLoader (DB + Redis)"""
    if use_synthetic:
        logger.warning("Synthetic data request ignored in favor of DB Architecture check.")
    
    logger.info("Initializing DataLoader (Connecting to DB/Redis)...")
    # Initialize connection pools manually since we are outside the app lifespan
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        
        db_url = os.getenv("DATABASE_URL")
        # In docker, DATABASE_URL should be set. If local, might fail if not exported.
        if not db_url:
             # Fallback for local testing if env not set, but inside docker it will work
             db_url = "postgresql://trader:trader@mtf-postgres:5432/mtf_db"
        
        db_pool = await asyncpg.create_pool(db_url)
        
        loader = DataLoader(db_pool, redis_client)
        
        # 1. Fetch Gold from DB
        logger.info("Fetching Gold (XAUUSD) from Database...")
        df = await loader.get_gold_data(limit=10000)
        
        # 2. Fetch Macro from YFinance (via Loader caching)
        logger.info("Fetching Macro Data (Oil, Yields, EURUSD)...")
        macro_df = await loader.get_macro_data(lookback_days=50)
        
        # Cleanup
        await db_pool.close()
        await redis_client.aclose()
        
        logger.info(f"Gold DB Range: {df.index.min()} to {df.index.max()}")
        if not macro_df.empty:
             logger.info(f"Macro YF Range: {macro_df.index.min()} to {macro_df.index.max()}")
        else:
             logger.warning("Macro YF DataFrame is empty!")

        if df.empty:
            raise ValueError("Database returned empty Gold data! Check data-pipeline.")
            
        # Align timestamps
        # Database is UTC, macro might be tz-aware or naive. 
        # Loader returns UTC for Gold. Macro from Loader is JSON -> DataFrame.
        
        # Macro index might need conversion if read_json didn't preserve it perfectly as datetime
        if not isinstance(macro_df.index, pd.DatetimeIndex):
             macro_df.index = pd.to_datetime(macro_df.index, utc=True)
        else:
             if macro_df.index.tz is None:
                 macro_df.index = macro_df.index.tz_localize('UTC')
             else:
                 macro_df.index = macro_df.index.tz_convert('UTC')
        
        common_idx = df.index.intersection(macro_df.index)
        logger.info(f"Exact intersection count: {len(common_idx)}")
        
        if len(common_idx) < 100:
             logger.warning(f"Low intersection ({len(common_idx)}) between Gold DB and Macro. alignment issue?")
             # Fallback: join using nearest (macro is daily, gold is hourly?)
             # Actually Gold DB is 1h timeframe? 
             # Let's resample Gold to Daily for the paper to match Macro or fill Macro to Hourly
             # Paper model uses hourly?
             # model_engine default lookback is 60 steps. If 1h, that's 2.5 days. 
             # If we want daily comparison, we should resample.
             # But let's assume we want to predict hourly Gold using daily Macro (ffill).
             pass

        # Reindex macro to match Gold (Hourly) using ffill
        macro_reindexed = macro_df.reindex(df.index, method='ffill').bfill()
        
        final_df = df
        final_macro = macro_reindexed
        
        # Drop any remaining NaNs (e.g. at start if macro missing)
        common_valid = final_df.index.intersection(final_macro.dropna().index)
        final_df = final_df.loc[common_valid]
        final_macro = final_macro.loc[common_valid]
        
        if final_df.empty:
             raise ValueError("Data empty after NaN drop.")
        
        logger.info(f"Loaded {len(final_df)} rows from DB with Macro features.")
        return final_df, final_macro

    except Exception as e:
        logger.error(f"Architecture Data Fetch Failed: {e}")
        raise e

def calculate_technical_features(df):
    """
    Add User-Requested Indicators:
    - Stochastic Oscillator (9, 3, 3)
    - Williams %R (14)
    - RSI (14)
    - MACD (12, 26, 9)
    - ATR (14)
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
    
    # 6. EMA (5, 10) - Gap Closure vs arXiv:2505.01402v1
    df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
    
    # 7. GARCH(1,1) Volatility - Phase 3 SOTA
    # Fit GARCH on returns to get conditional volatility
    returns = 100 * df['close'].pct_change().dropna()
    # Using a fixed window fit for feature generation (conditional vol depends on past only)
    try:
        am = arch_model(returns, vol='Garch', p=1, o=0, q=1, dist='Normal')
        res = am.fit(disp='off')
        # Realign volatility to original index
        vol = res.conditional_volatility
        df.loc[returns.index, 'garch_vol'] = vol
    except Exception as e:
        logger.warning(f"GARCH fitting failed: {e}")
        df['garch_vol'] = 0
        
    return df.dropna()

def evaluate_metrics(actual, predicted):
    # Ensure no zeros/NaNs in actual for MAPE
    mask = actual != 0
    actual = actual[mask]
    predicted = predicted[mask]
    
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    mae = mean_absolute_error(actual, predicted)
    
    # User's Primary Metric: MAPE
    mape = np.mean(np.abs((actual - predicted) / actual)) * 100
    accuracy = 100 - mape  # "Forecast Accuracy" definition
    
    # Directional Accuracy
    actual_diff = np.diff(actual)
    pred_diff = np.diff(predicted)
    correct_direction = np.sign(actual_diff) == np.sign(pred_diff)
    da = np.mean(correct_direction) * 100
    
    return {"RMSE": rmse, "MAE": mae, "MAPE (%)": mape, "Accuracy (1-MAPE) %": accuracy, "Directional Accuracy (%)": da}

class Baselines:
    @staticmethod
    def train_sarimax(df):
        logger.info("Training Baseline SARIMAX...")
        # Reduce memory usage / speed up for paper script
        model = SARIMAX(df['close'].values, order=(1,1,1), seasonal_order=(0,0,0,0))
        results = model.fit(disp=False)
        return results

async def run_experiments():
    logger.info("--- Starting Paper Experiments (High-Precision Mode) ---")
    
    # 1. Data Loading
    df, macro_df = await fetch_data(use_synthetic=False)
    
    # 2. Feature Engineering
    logger.info("Calculating Technical Indicators (Stoch, Williams, RSI, MACD)...")
    df = calculate_technical_features(df)
    
    # Identify Technical Columns
    tech_cols = ['stoch_k', 'stoch_d', 'stoch_d_smooth', 'williams_r', 'rsi', 'macd', 'macd_signal', 'atr', 'ema_5', 'ema_10', 'garch_vol']
    
    # Re-align after dropna
    common_idx = df.index.intersection(macro_df.index)
    df = df.loc[common_idx]
    macro_df = macro_df.loc[common_idx]
    
    # Merge Technicals into Macro (for feature selection)
    feature_df = macro_df.copy()
    feature_df = feature_df.join(df[tech_cols])
    
    # Split Data (80/20)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    train_features = feature_df.iloc[:split_idx]
    test_features = feature_df.iloc[split_idx:]
    
    actuals = test_df['close'].values
    
    if len(actuals) < 100:
        logger.warning(f"Test set too small ({len(actuals)}), reducing forecast steps.")
        forecast_steps = len(actuals)
    else:
        forecast_steps = 100
    
    # 3. Hybrid Model (Ours)
    logger.info("--- Running Hybrid Model Experiment ---")
    predictor = HybridPredictor(model_dir="paper_models")
    
    # Train
    predictor.train(train_df, macro_df=train_features)
    
    # Forecast
    hybrid_res = predictor.predict(steps=forecast_steps, macro_df=test_features)
    hybrid_pred = hybrid_res['total']
    
    # 4. Baseline: SARIMAX Only
    logger.info("--- Running SARIMAX Baseline ---")
    sarimax_model = Baselines.train_sarimax(train_df)
    sarimax_pred = sarimax_model.forecast(steps=forecast_steps)
    
    # 5. Metrics
    test_actuals = actuals[:forecast_steps]
    
    # Ensure baseline and hybrid preds are same length as actuals
    # (Sometimes forecast steps might differ by 1)
    min_len = min(len(test_actuals), len(hybrid_pred), len(sarimax_pred))
    test_actuals = test_actuals[:min_len]
    hybrid_pred = np.array(hybrid_pred)[:min_len]
    sarimax_pred = np.array(sarimax_pred)[:min_len] # SARIMAX returns np.ndarray if trained on values
    
    metrics_hybrid = evaluate_metrics(test_actuals, hybrid_pred)
    metrics_sarimax = evaluate_metrics(test_actuals, sarimax_pred)
    
    # 6. Visualization
    plt.figure(figsize=(12, 6))
    plt.plot(test_actuals, label='Actual Data', color='black')
    plt.plot(hybrid_pred, label=f'Hybrid (Acc={metrics_hybrid["Accuracy (1-MAPE) %"]:.2f}%)', color='blue', linestyle='--')
    plt.plot(sarimax_pred, label=f'SARIMAX (Acc={metrics_sarimax["Accuracy (1-MAPE) %"]:.2f}%)', color='red', linestyle=':')
    plt.title("Gold Price Forecasting: Hybrid vs Baseline (High-Precision w/ Technicals)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{RESULTS_DIR}/forecast_comparison_high_precision.png")
    
    # Generate Report Table
    results_df = pd.DataFrame([metrics_sarimax, metrics_hybrid], index=['SARIMAX', 'Hybrid (Ours)'])
    results_df.to_csv(f"{RESULTS_DIR}/metrics_comparison.csv")
    
    print("\n=== Experiment Results ===")
    print(results_df)

if __name__ == "__main__":
    asyncio.run(run_experiments())
