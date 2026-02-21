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
from src.app.domain.transformers import LogReturnTransformer

import asyncpg
import redis.asyncio as redis
import torch

import matplotlib
matplotlib.use('Agg') # Headless
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("olympus-predictor.simulation")

async def run_simulation(symbol: str = "XAUUSD", timeframe: str = "M15", lookback_days: int = 180, steps=5):
    """
    Run an exhaustive walk-forward historical simulation (1-step stride).
    """
    logger.info(f"🚀 Starting Exhaustive Stress Test for {symbol} - coverage: {lookback_days} days")
    
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    db_pool = await asyncpg.create_pool(settings.DATABASE_URL)
    
    try:
        loader = DataLoader(db_pool, redis_client)
        predictor = HybridPredictor(model_dir=settings.MODEL_DIR)
        predictor.load_models()
        
        # 1. Fetch Complete Dataset
        df_gold = await loader.get_gold_data(limit=10000)
        df_macro = await loader.get_macro_data(lookback_days=lookback_days)
        df_sent = await loader.get_sentiment_data(symbol=symbol, lookback_days=lookback_days)
        
        if df_gold.empty:
            logger.error("❌ No Gold data.")
            return

        window_size = predictor.lookback 
        df_sim = df_gold.reset_index()
        total_steps = len(df_sim) - steps - window_size
        
        results = []
        full_actuals = []
        full_preds = []
        ts_indices = []
        pnl_tracking = [100.0] # Simulated equity
        
        logger.info(f"⏳ Processing {total_steps} windows (STRIDE: 1)")
        
        predictor.lstm_model.eval()
        
        for i in range(0, total_steps, 1): 
            current_idx = window_size + i
            sim_now_ts = df_sim.iloc[current_idx]['timestamp']
            historical_window = df_sim.iloc[current_idx - window_size : current_idx]
            actual_future = df_sim.iloc[current_idx : current_idx + steps]
            actual_prices = actual_future['close'].values
            last_price = historical_window.iloc[-1]['close']
            
            try:
                sarimax_forecast_lr = predictor.sarimax_model.forecast(steps=steps)
                recent_residuals = predictor.sarimax_model.resid[-window_size:] 
                recent_resid_scaled = predictor.scaler.transform(recent_residuals.reshape(-1, 1))
                
                exog_window = df_macro.reindex(historical_window['timestamp']).ffill().bfill()
                if not df_sent.empty:
                    exog_window['sentiment'] = df_sent.reindex(historical_window['timestamp']).ffill().bfill()['score']
                else:
                    exog_window['sentiment'] = 0.0
                
                exog_transformed = predictor.feature_engine.transform(exog_window)
                exog_scaled = predictor.exog_scaler.transform(exog_transformed.values)
                regime_scaled = np.full((window_size, 1), 0.0) 
                
                lstm_input_np = np.hstack([recent_resid_scaled, exog_scaled, regime_scaled])
                curr_input = torch.from_numpy(lstm_input_np).float().view(1, window_size, -1).to(predictor.device)
                
                residual_means = []
                with torch.no_grad():
                    for _ in range(steps):
                        mean, _ = predictor.lstm_model(curr_input)
                        residual_means.append(mean.item())
                        next_exog = torch.from_numpy(exog_scaled[-1:]).float().to(predictor.device).unsqueeze(0)
                        next_regime = torch.from_numpy(regime_scaled[-1:]).float().to(predictor.device).unsqueeze(0)
                        new_residual = mean.view(1, 1, 1)
                        new_step = torch.cat([new_residual, next_exog, next_regime], dim=2)
                        curr_input = torch.cat((curr_input[:, 1:, :], new_step), dim=1)
                
                res_means_scaled = np.array(residual_means).reshape(-1, 1)
                res_final_lr = predictor.scaler.inverse_transform(res_means_scaled).flatten()
                
                total_lr = sarimax_forecast_lr + res_final_lr
                pred_prices = LogReturnTransformer.inverse_transform(last_price, total_lr)
                
                # Metrics & PnL
                mape = np.mean(np.abs((actual_prices - pred_prices) / actual_prices)) * 100
                actual_ret = (actual_prices[0] - last_price) / last_price
                pred_ret = (pred_prices[0] - last_price) / last_price
                hit = 1 if np.sign(actual_ret) == np.sign(pred_ret) else 0
                
                # Pseudo-PnL (long/short based on prediction)
                trade_ret = actual_ret if pred_ret > 0 else -actual_ret
                pnl_tracking.append(pnl_tracking[-1] * (1 + trade_ret))
                
                results.append({"timestamp": sim_now_ts, "mape": mape, "hit": hit})
                full_actuals.append(actual_prices[0])
                full_preds.append(pred_prices[0])
                ts_indices.append(sim_now_ts)
                
            except Exception:
                continue

        if results:
            res_df = pd.DataFrame(results)
            pnl_final = np.array(pnl_tracking)
            cum_returns = (pnl_final[1:] - pnl_final[:-1]) / pnl_final[:-1]
            sharpe = (np.mean(cum_returns) / np.std(cum_returns) * np.sqrt(252 * 96)) if np.std(cum_returns) > 0 else 0
            
            # Max Drawdown
            peaks = np.maximum.accumulate(pnl_final)
            drawdowns = (peaks - pnl_final) / peaks
            max_dd = np.max(drawdowns) * 100

            report = {
                "windows": len(res_df),
                "avg_mape": round(res_df['mape'].mean(), 4),
                "hit_ratio": round(res_df['hit'].mean() * 100, 2),
                "simulated_sharpe": round(sharpe, 2),
                "max_drawdown_pct": round(max_dd, 2)
            }
            print(json.dumps(report, indent=2))
            
            # --- VISUALIZATION ---
            logger.info("🎨 Generating Global Simulation Visuals...")
            sns.set_theme(style="darkgrid")
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
            
            subset_n = 500 # Slightly more for global view
            ax1.plot(ts_indices[-subset_n:], full_actuals[-subset_n:], label="Actual", color="black", alpha=0.7)
            ax1.plot(ts_indices[-subset_n:], full_preds[-subset_n:], label="Forecast", color="#00ffcc", linestyle="--")
            ax1.set_title(f"Price Accuracy (Last {subset_n} windows)")
            ax1.legend()

            ax2.plot(ts_indices[-subset_n:], pnl_final[-subset_n-1:-1], label="Simulated Equity", color="#ffcc00")
            ax2.set_title("Simulated Equity Growth (Base 100)")
            ax2.legend()
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            os.makedirs("paper_results", exist_ok=True)
            plt.savefig(f"paper_results/sim_exhaustive_{symbol}.png", dpi=200)
            logger.info(f"✅ Exhaustive Report & Visual Saved.")
            
    finally:
        await redis_client.close()
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(run_simulation())
