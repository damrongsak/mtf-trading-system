import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
from datetime import datetime, timedelta
import logging

# Add workspace to path
sys.path.insert(0, '/home/dan/workspace/mtf-trading-system/services/strategy-core')

from app.analysis.liquidity import LiquidityAnalyzer, calculate_atr_stop_loss, calculate_volatility_scaled_position
from app.indicators.smc import detect_order_blocks, detect_fvg, detect_structure
from app.logic import SignalDirection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_data(symbol: str, timeframe: str, period: str = "5d"):
    """Fetch historical data using yfinance."""
    interval_map = {
        "M15": "15m",
        "H1": "1h",
        "H4": "1h", # yf doesn't have 4h, will resample
        "D1": "1d"
    }
    interval = interval_map.get(timeframe, "1h")
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    
    # Handle multi-index columns if needed
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df.columns = [col.lower() for col in df.columns]
    
    if timeframe == "H4":
        df = df.resample('4H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
    return df

def run_strategy(symbol: str = "GC=F"):
    """
    Main Strategy Loop:
    1. Phase 0: HTF Bias (H1/H4)
    2. Phase 1: M15 Liquidity Sweep (BSL/SSL)
    3. Phase 2: M15 CHoCH Shift
    4. Phase 3: M15 OB/FVG Entry
    """
    logger.info(f"Starting Professional SMC Strategy for {symbol}...")
    
    # 1. Fetch Data
    df_h4 = fetch_data(symbol, "H4", period="60d")
    df_h1 = fetch_data(symbol, "H1", period="60d")
    df_m15 = fetch_data(symbol, "M15", period="30d")
    
    if df_m15.empty or df_h1.empty:
        logger.error("Data fetch failed.")
        return

    # 2. HTF Bias Filter
    # Check H1 EMA 200
    from app.indicators.trend import calculate_ema
    ema_h1 = calculate_ema(df_h1['close'], span=200)
    last_close_h1 = df_h1['close'].iloc[-1]
    last_ema_h1 = ema_h1.iloc[-1]
    
    bias = SignalDirection.NEUTRAL
    if last_close_h1 > last_ema_h1:
        bias = SignalDirection.BULLISH
    elif last_close_h1 < last_ema_h1:
        bias = SignalDirection.BEARISH
    
    logger.info(f"HTF Bias: {bias.value}")

    # 3. Liquidity Analysis (M15)
    liq = LiquidityAnalyzer(fractal_window=5)
    pivots = liq.find_swing_points(df_m15)
    grabs = liq.detect_liquidity_grabs(df_m15, pivots)
    
    # 4. Filter Grabs by Bias
    active_grab = None
    if bias == SignalDirection.BULLISH:
        # Looking for Bullish Grab (SSL Liquidation)
        bullish_grabs = [g for g in grabs if g['type'] == 'bullish_grab']
        if bullish_grabs:
            active_grab = bullish_grabs[-1]
    elif bias == SignalDirection.BEARISH:
        # Looking for Bearish Grab (BSL Liquidation)
        bearish_grabs = [g for g in grabs if g['type'] == 'bearish_grab']
        if bearish_grabs:
            active_grab = bearish_grabs[-1]

    if not active_grab:
        logger.info("No valid Liquidity Grab detected aligning with Bias.")
        # For visualization purposes, we'll continue to show the chart anyway.
    else:
        logger.info(f"ALARM: Valid {active_grab['type']} detected! {active_grab['description']}")

    # 5. Market Structure & Zones
    obs = detect_order_blocks(df_m15)
    fvgs = detect_fvg(df_m15)
    structure = detect_structure(df_m15, window=3)
    
    # Visual Overlay Preparation
    # We want to highlight BSL/SSL pivots
    bsl_prices = [np.nan] * len(df_m15)
    ssl_prices = [np.nan] * len(df_m15)
    
    for h in pivots['highs']:
        if h['index'] < len(df_m15):
            bsl_prices[h['index']] = h['price']
    for l in pivots['lows']:
        if l['index'] < len(df_m15):
            ssl_prices[l['index']] = l['price']

    # 6. Visualization with mplfinance
    # Create extra plots (BSL/SSL)
    apd = [
        mpf.make_addplot(bsl_prices, type='scatter', markersize=50, marker='v', color='red', label='BSL'),
        mpf.make_addplot(ssl_prices, type='scatter', markersize=50, marker='^', color='green', label='SSL')
    ]
    
    # Draw Order Blocks as Horizontal Lines (last 5 unmitigated)
    unmitigated_obs = [ob for ob in obs if not ob.get('mitigated')][-5:]
    hlines = []
    hcolors = []
    for ob in unmitigated_obs:
        hlines.append(ob['top'])
        hlines.append(ob['bottom'])
        hcolors.append('rgba(0,255,0,0.2)' if ob['type'] == 'bullish' else 'rgba(255,0,0,0.2)')

    # Save chart
    output_path = "/home/dan/workspace/mtf-trading-system/services/strategy-core/artifacts/smc_liquidity_test.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Filter for last 150 candles for clarity
    plot_df = df_m15.iloc[-150:]
    
    # Re-calculate pivot arrays for sliced df
    bsl_plot = [np.nan] * len(plot_df)
    ssl_plot = [np.nan] * len(plot_df)
    
    start_idx = len(df_m15) - 150
    for h in pivots['highs']:
        if h['index'] >= start_idx:
            bsl_plot[h['index'] - start_idx] = h['price']
    for l in pivots['lows']:
        if l['index'] >= start_idx:
            ssl_plot[l['index'] - start_idx] = l['price']
            
    plot_apd = [
        mpf.make_addplot(bsl_plot, type='scatter', markersize=50, marker='v', color='red', label='BSL'),
        mpf.make_addplot(ssl_plot, type='scatter', markersize=50, marker='^', color='green', label='SSL')
    ]

    mpf.plot(plot_df, type='candle', style='charles', 
             title=f"XAUUSD SMC + Liquidity Sweep ({bias.value} Bias)",
             ylabel='Price',
             addplot=plot_apd,
             savefig=output_path)
    
    logger.info(f"Chart generated at {output_path}")
    
    # Risk Calculation Demo
    if active_grab:
        # Find nearest OB after sweep for entry
        direction = "BULLISH" if active_grab['type'] == 'bullish_grab' else "BEARISH"
        relevant_obs = [ob for ob in obs if ob['type'].upper() == direction]
        if relevant_obs:
            target_ob = relevant_obs[-1]
            sl = calculate_atr_stop_loss(df_m15, target_ob, direction)
            
            # 1% Risk on 100k account
            risk_amt = 1000.0
            from app.indicators import calculate_atr
            atr_val = calculate_atr(df_m15['high'], df_m15['low'], df_m15['close']).iloc[-1]
            
            pos_size = calculate_volatility_scaled_position(risk_amt, df_m15['close'].iloc[-1], sl, atr_val)
            
            logger.info("=== TRADE PLAN ===")
            logger.info(f"Direction: {direction}")
            logger.info(f"Entry: {df_m15['close'].iloc[-1]:.2f}")
            logger.info(f"Structural SL (ATR Buffer): {sl:.2f}")
            logger.info(f"Volatility Scaled Size: {pos_size} lots")
            logger.info("==================")

if __name__ == "__main__":
    run_strategy("GC=F")
