import asyncio
import pandas as pd
import numpy as np
import sys
import os
import json
import logging
from datetime import datetime
import torch
import torch.distributions as dist
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import asyncpg
import redis.asyncio as redis

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app.domain.models import HybridPredictor
from src.app.infrastructure.data_loader import DataLoader
from src.app.core.config import settings
from src.app.domain.transformers import LogReturnTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("olympus-predictor.monte-carlo")

async def run_monte_carlo(symbol: str = "XAUUSD", n_trials: int = 10000, steps: int = 24):
    """
    Perform Monte Carlo Probabilistic Simulation using LSTM uncertainty.
    """
    logger.info(f"🎲 Starting Monte Carlo Simulation: {n_trials} trials, {steps} steps horizon")
    
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    db_pool = await asyncpg.create_pool(settings.DATABASE_URL)
    
    try:
        loader = DataLoader(db_pool, redis_client)
        predictor = HybridPredictor(model_dir=settings.MODEL_DIR)
        predictor.load_models()
        
        # 1. Fetch Current State
        df_gold = await loader.get_gold_data(limit=predictor.lookback + 1)
        df_macro = await loader.get_macro_data(lookback_days=7)
        df_sent = await loader.get_sentiment_data(symbol=symbol, lookback_days=7)
        
        if df_gold.empty:
            logger.error("❌ No data for state reconstruction.")
            return

        window_size = predictor.lookback
        last_price = df_gold.iloc[-1]['close']
        
        # A. Baseline Forecast (Deterministic SARIMAX)
        # We assume SARIMAX mean as the base path for residuals
        sarimax_forecast_lr = predictor.sarimax_model.forecast(steps=steps)
        
        # B. Initial State Construction
        recent_residuals = predictor.sarimax_model.resid[-window_size:]
        recent_resid_scaled = predictor.scaler.transform(recent_residuals.reshape(-1, 1))
        
        # Align Exog Features
        exog_window = df_macro.reindex(df_gold.tail(window_size).index).ffill().bfill()
        if not df_sent.empty:
            exog_window['sentiment'] = df_sent.reindex(df_gold.tail(window_size).index).ffill().bfill()['score']
        else:
            exog_window['sentiment'] = 0.0
            
        exog_transformed = predictor.feature_engine.transform(exog_window)
        exog_scaled = predictor.exog_scaler.transform(exog_transformed.values)
        regime_scaled = np.full((window_size, 1), 0.0) # Normal state
        
        # Combine to 8D State
        state_np = np.hstack([recent_resid_scaled, exog_scaled, regime_scaled])
        
        # Repeat state for all trials (Batching)
        # Shape: (N_TRIALS, window_size, 8)
        state_tensor = torch.from_numpy(state_np).float().to(predictor.device)
        state_batch = state_tensor.unsqueeze(0).repeat(n_trials, 1, 1)
        
        # C. Stochastic Simulation Loop
        simulated_paths = [] # Shape: (N_TRIALS, steps)
        current_state = state_batch
        
        all_trials_lr = [] # To accumulate log-returns
        
        predictor.lstm_model.eval()
        with torch.no_grad():
            for t in range(steps):
                # 1. Predict next step Mean & Std
                mu, sigma = predictor.lstm_model(current_state) # mu/sigma shape: (N_TRIALS, 1)
                
                # 2. Sample from Normal Distribution
                # Each trial draws its own sample
                epsilon = torch.randn_like(mu)
                sampled_residual_scaled = mu + epsilon * sigma
                
                # 3. Store for inverse transform
                all_trials_lr.append(sampled_residual_scaled.cpu().numpy())
                
                # 4. Update Current State (Roll window)
                # For simplicity, exogenous features are kept constant at last known value
                # (In a more complex version, we'd use macro_forecaster)
                next_exog = torch.from_numpy(exog_scaled[-1:]).float().to(predictor.device).unsqueeze(0).repeat(n_trials, 1, 1)
                next_regime = torch.from_numpy(regime_scaled[-1:]).float().to(predictor.device).unsqueeze(0).repeat(n_trials, 1, 1)
                
                new_step = torch.cat([sampled_residual_scaled.unsqueeze(1), next_exog, next_regime], dim=2)
                current_state = torch.cat([current_state[:, 1:, :], new_step], dim=1)
        
        # D. Post-Processing & Inverse Transform
        # trials_lr_scaled shape: (steps, N_TRIALS, 1) -> (N_TRIALS, steps)
        trials_lr_scaled = np.array(all_trials_lr).squeeze().T
        
        # Inverse Scale Residuals
        residual_paths_lr = predictor.scaler.inverse_transform(trials_lr_scaled.reshape(-1, 1)).reshape(n_trials, steps)
        
        # Combine with SARIMAX baseline
        total_paths_lr = sarimax_forecast_lr + residual_paths_lr
        
        # Accumulate Price Paths
        price_paths = []
        for trial in range(n_trials):
            trial_prices = LogReturnTransformer.inverse_transform(last_price, total_paths_lr[trial])
            price_paths.append(trial_prices)
            
        price_paths = np.array(price_paths) # (N_TRIALS, steps)
        
        # E. Risk Statistics
        terminal_prices = price_paths[:, -1]
        returns = (terminal_prices - last_price) / last_price
        
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean()
        prob_profit = (returns > 0).mean() * 100
        
        report = {
            "last_price": last_price,
            "horizon_steps": steps,
            "var_95_pct": round(var_95 * 100, 4),
            "cvar_95_pct": round(cvar_95 * 100, 4),
            "prob_profit_pct": round(prob_profit, 2),
            "mean_terminal_price": round(float(terminal_prices.mean()), 2),
            "std_terminal_price": round(float(terminal_prices.std()), 2)
        }
        print(json.dumps(report, indent=2))
        
        # F. Visualizations
        logger.info("🎨 Generating Probabilistic Analytics...")
        sns.set_theme(style="darkgrid")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))
        
        # 1. Fan Chart
        time_steps = np.arange(steps + 1)
        # Prepend last_price to paths
        full_paths = np.hstack([np.full((n_trials, 1), last_price), price_paths])
        
        # Percentiles
        p5 = np.percentile(full_paths, 5, axis=0)
        p25 = np.percentile(full_paths, 25, axis=0)
        p50 = np.percentile(full_paths, 50, axis=0)
        p75 = np.percentile(full_paths, 75, axis=0)
        p95 = np.percentile(full_paths, 95, axis=0)
        
        ax1.plot(time_steps, p50, color="black", label="Median Path", linewidth=2)
        ax1.fill_between(time_steps, p25, p75, color="#00ffcc", alpha=0.3, label="50% Confidence")
        ax1.fill_between(time_steps, p5, p95, color="#00ffcc", alpha=0.1, label="90% Confidence")
        ax1.set_title(f"Olympus Monte Carlo Fan Chart: {symbol} Future Projections", fontsize=14)
        ax1.set_ylabel("Price")
        ax1.legend()
        
        # 2. Histogram
        sns.histplot(returns * 100, kde=True, ax=ax2, color="#ffcc00", bins=50)
        ax2.axvline(var_95 * 100, color="red", linestyle="--", label=f"VaR 95%: {var_95*100:.2f}%")
        ax2.axvline(0, color="black", linestyle="-", alpha=0.5)
        ax2.set_title("Simulated Return Distribution (Horizon: 24 steps)", fontsize=14)
        ax2.set_xlabel("Return (%)")
        ax2.legend()
        
        plt.tight_layout()
        os.makedirs("paper_results", exist_ok=True)
        plt.savefig(f"paper_results/monte_carlo_{symbol}_{steps}.png", dpi=200)
        logger.info(f"✅ Monte Carlo Analytics Saved.")
        
    finally:
        await redis_client.close()
        await db_pool.close()

if __name__ == "__main__":
    # Default: 24 steps (approx 6 hours at M15)
    asyncio.run(run_monte_carlo(steps=24))
