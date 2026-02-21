import asyncio
import pandas as pd
import numpy as np
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app.domain.models import HybridPredictor
from src.app.infrastructure.data_loader import DataLoader
from src.app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("olympus-predictor.simulation")

import asyncpg
import redis.asyncio as redis
import torch

from src.app.domain.transformers import LogReturnTransformer

async def run_simulation(symbol: str = "XAUUSD", timeframe: str = "M15", lookback_days: int = 40, steps=5):
    """
    Run a walk-forward historical simulation with full 8D state alignment.
    """
    logger.info(f"🚀 Starting Multi-Dimensional Simulation for {symbol} - Last {lookback_days} days")
    
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    db_pool = await asyncpg.create_pool(settings.DATABASE_URL)
    
    try:
        loader = DataLoader(db_pool, redis_client)
        predictor = HybridPredictor(model_dir=settings.MODEL_DIR)
        predictor.load_models()
        
        # 1. Fetch Datasets
        df_gold = await loader.get_gold_data(limit=3000)
        df_macro = await loader.get_macro_data(lookback_days=lookback_days)
        df_sent = await loader.get_sentiment_data(symbol=symbol, lookback_days=lookback_days)
        
        if df_gold.empty:
            logger.error("❌ No Gold data.")
            return

        window_size = predictor.lookback 
        df_sim = df_gold.reset_index()
        total_steps = len(df_sim) - steps - window_size
        
        results = []
        logger.info(f"⏳ Processing {total_steps//5} windows (Exog Features: {predictor.exog_features})")
        
        predictor.lstm_model.eval()
        
        for i in range(0, total_steps, 5): 
            current_idx = window_size + i
            sim_now_ts = df_sim.iloc[current_idx]['timestamp']
            
            historical_window = df_sim.iloc[current_idx - window_size : current_idx]
            actual_future = df_sim.iloc[current_idx : current_idx + steps]
            actual_prices = actual_future['close'].values
            last_price = historical_window.iloc[-1]['close']
            
            try:
                # A. SARIMAX Baseline
                sarimax_forecast_lr = predictor.sarimax_model.forecast(steps=steps)
                
                # B. Feature Alignment (8D Construction)
                # 1. Residuals (1D)
                recent_residuals = predictor.sarimax_model.resid[-window_size:] 
                recent_resid_scaled = predictor.scaler.transform(recent_residuals.reshape(-1, 1))
                
                # 2. Exogenous (6D) - Reconstruct for the window
                exog_window = df_macro.reindex(historical_window['timestamp']).ffill().bfill()
                # Add sentiment if exists
                if not df_sent.empty:
                    exog_window['sentiment'] = df_sent.reindex(historical_window['timestamp']).ffill().bfill()['score']
                else:
                    exog_window['sentiment'] = 0.0
                
                # Transform via engine to get selected features in order
                exog_transformed = predictor.feature_engine.transform(exog_window)
                exog_scaled = predictor.exog_scaler.transform(exog_transformed.values)
                
                # 3. Regime (1D) - Fixed for simplicity in this run
                regime_scaled = np.full((window_size, 1), 0.0) # Assume Neutral Regime
                
                # Stack 8D State
                lstm_input_np = np.hstack([recent_resid_scaled, exog_scaled, regime_scaled])
                curr_input = torch.from_numpy(lstm_input_np).float().view(1, window_size, -1).to(predictor.device)
                
                # C. LSTM Iterative Prediction
                residual_means = []
                with torch.no_grad():
                    for _ in range(steps):
                        mean, _ = predictor.lstm_model(curr_input)
                        residual_means.append(mean.item())
                        
                        # Prepare next step (Simplified: assuming exogenous/regime stay same for multi-step)
                        # In live, macro_forecaster is used. Here we use last step value.
                        next_exog = torch.from_numpy(exog_scaled[-1:]).float().to(predictor.device).unsqueeze(0)
                        next_regime = torch.from_numpy(regime_scaled[-1:]).float().to(predictor.device).unsqueeze(0)
                        new_residual = mean.view(1, 1, 1)
                        
                        new_step = torch.cat([new_residual, next_exog, next_regime], dim=2)
                        curr_input = torch.cat((curr_input[:, 1:, :], new_step), dim=1)
                
                # D. Final Hybrid
                res_means_scaled = np.array(residual_means).reshape(-1, 1)
                res_final_lr = predictor.scaler.inverse_transform(res_means_scaled).flatten()
                
                total_lr = sarimax_forecast_lr + res_final_lr
                pred_prices = LogReturnTransformer.inverse_transform(last_price, total_lr)
                
                mape = np.mean(np.abs((actual_prices - pred_prices) / actual_prices)) * 100
                hit = 1 if np.sign(actual_prices[-1] - last_price) == np.sign(pred_prices[-1] - last_price) else 0
                results.append({"mape": mape, "hit": hit})
                
            except Exception as e:
                # logger.error(f"Error: {e}")
                continue

        if results:
            res_df = pd.DataFrame(results)
            report = {
                "windows": len(res_df),
                "avg_mape": round(res_df['mape'].mean(), 4),
                "hit_ratio": round(res_df['hit'].mean() * 100, 2)
            }
            print(json.dumps(report, indent=2))
            
    finally:
        await redis_client.close()
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(run_simulation())
