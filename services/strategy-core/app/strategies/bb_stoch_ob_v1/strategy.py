"""
BB_Stochastic_OB - Bollinger Bands + Stochastic + Order Block Strategy
=====================================================================
A professional-grade trading strategy combining:
- Bollinger Bands (13, 1.5) for volatility-based entries
- Stochastic Oscillator (9, 3, 3) for momentum confirmation
- Order Block (SMC) for institutional footprint confirmation

Author: Soda (Olympus AI)
Date: 2026-03-18
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

METADATA = {
    "name": "BB Stochastic Order Block (SMC)",
    "description": "Mean Reversion with Order Block Confirmation - Buy when BB oversold + Stoch oversold + near OB zone",
    "version": "1.0.0",
    "author": "Soda (Olympus AI)",
    "defaults": {
        "bb_period": 13,
        "bb_std": 1.5,
        "stoch_k": 9,
        "stoch_d": 3,
        "stoch_oversold": 20,
        "stoch_overbought": 80,
        "ob_lookback": 15,
        "ob_tolerance": 0.008,  # 0.8% price tolerance for OB zones
        "risk_per_trade": 0.01,  # 1% risk per trade
        "atr_multiplier": 2.0    # ATR-based stop loss
    }
}


def calculate_bollinger_bands(prices: pd.Series, period: int = 13, std_dev: float = 1.5) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    return sma, upper_band, lower_band


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 9, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic Oscillator (%K and %D)"""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period).mean()
    
    return k, d


def find_order_blocks(open_prices: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, lookback: int = 15) -> list:
    """
    Find Order Blocks (SMC concept)
    Bullish OB: Bear candle (close < open) followed by 2+ bullish candles breaking high
    Bearish OB: Bull candle (close > open) followed by 2+ bearish candles breaking low
    """
    order_blocks = []
    
    for i in range(lookback + 5, len(close) - 3):
        # Bullish Order Block
        if close.iloc[i] < open_prices.iloc[i]:  # Bear candle
            if close.iloc[i+1] > open_prices.iloc[i+1] and close.iloc[i+2] > open_prices.iloc[i+2]:
                if high.iloc[i+2] > high.iloc[i]:
                    order_blocks.append({
                        "type": "BULLISH",
                        "high": high.iloc[i],
                        "low": low.iloc[i],
                        "index": i
                    })
        
        # Bearish Order Block
        elif close.iloc[i] > open_prices.iloc[i]:  # Bull candle
            if close.iloc[i+1] < open_prices.iloc[i+1] and close.iloc[i+2] < open_prices.iloc[i+2]:
                if low.iloc[i+2] < low.iloc[i]:
                    order_blocks.append({
                        "type": "BEARISH",
                        "high": high.iloc[i],
                        "low": low.iloc[i],
                        "index": i
                    })
    
    return order_blocks


def check_near_ob_zone(price: float, order_blocks: list, tolerance: float = 0.008) -> bool:
    """Check if price is near an Order Block zone"""
    for ob in order_blocks:
        if abs(price - ob['low']) / price < tolerance or abs(price - ob['high']) / price < tolerance:
            return True
    return False


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def strategy(data: pd.DataFrame, params: Optional[Dict[str, Any]] = None) -> Tuple[pd.Series, pd.Series, Dict[str, Any]]:
    """
    Main Strategy Function
    
    Entry Criteria (LONG):
        1. Price < Lower Bollinger Band (oversold)
        2. Stochastic K < oversold threshold (default 20)
        3. Price near Order Block zone (institutional confirmation)
    
    Exit Criteria:
        1. Price > Upper Bollinger Band, OR
        2. Stochastic K > overbought threshold (default 80)
    
    Args:
        data: pd.DataFrame with columns [open, high, low, close, volume]
        params: dict with strategy parameters
    
    Returns:
        entries: pd.Series (boolean)
        exits: pd.Series (boolean)
        signal_dict: dict with signal information
    """
    if params is None:
        params = {}
    
    # Load parameters
    defaults = METADATA["defaults"]
    bb_period = int(params.get('bb_period', defaults['bb_period']))
    bb_std = float(params.get('bb_std', defaults['bb_std']))
    stoch_k = int(params.get('stoch_k', defaults['stoch_k']))
    stoch_d = int(params.get('stoch_d', defaults['stoch_d']))
    stoch_oversold = int(params.get('stoch_oversold', defaults['stoch_oversold']))
    stoch_overbought = int(params.get('stoch_overbought', defaults['stoch_overbought']))
    ob_lookback = int(params.get('ob_lookback', defaults['ob_lookback']))
    ob_tolerance = float(params.get('ob_tolerance', defaults['ob_tolerance']))
    
    # Validate data
    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in data.columns for col in required_cols):
        logger.error(f"Missing required columns. Got: {data.columns.tolist()}")
        return None, None, None
    
    if len(data) < bb_period + stoch_k + 10:
        logger.warning(f"Insufficient data: {len(data)} bars")
        return None, None, None
    
    try:
        close = data['close']
        high = data['high']
        low = data['low']
        open_prices = data['open']
        
        # 1. Calculate Indicators
        bb_sma, bb_upper, bb_lower = calculate_bollinger_bands(close, bb_period, bb_std)
        stoch_k_series, stoch_d_series = calculate_stochastic(high, low, close, stoch_k, stoch_d)
        atr = calculate_atr(high, low, close)
        
        # 2. Find Order Blocks (last N)
        all_ob = find_order_blocks(open_prices, high, low, close, ob_lookback)
        recent_ob = all_ob[-15:] if len(all_ob) > 15 else all_ob  # Last 15 OBs
        
        # 3. Generate Signals
        entries = pd.Series(False, index=data.index)
        exits = pd.Series(False, index=data.index)
        
        for i in range(bb_period + stoch_k + 5, len(data)):
            current_price = close.iloc[i]
            current_bb_sma = bb_sma.iloc[i]
            current_bb_upper = bb_upper.iloc[i]
            current_bb_lower = bb_lower.iloc[i]
            current_stoch_k = stoch_k_series.iloc[i]
            
            # Check if near OB zone
            near_ob = check_near_ob_zone(current_price, recent_ob, ob_tolerance)
            
            # LONG Entry: BB oversold + Stoch oversold + near OB
            if (current_price < current_bb_lower and 
                current_stoch_k < stoch_oversold and 
                near_ob):
                entries.iloc[i] = True
            
            # Exit: BB overbought OR Stoch overbought
            if current_price > current_bb_upper or current_stoch_k > stoch_overbought:
                exits.iloc[i] = True
        
        # 4. Current Signal (Live Context)
        current_price = close.iloc[-1]
        current_bb_sma = bb_sma.iloc[-1]
        current_bb_upper = bb_upper.iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_stoch_k = stoch_k_series.iloc[-1]
        current_stoch_d = stoch_d_series.iloc[-1]
        current_atr = atr.iloc[-1]
        
        near_ob = check_near_ob_zone(current_price, recent_ob, ob_tolerance)
        
        direction = None
        reason = ""
        stop_loss = None
        take_profit = None
        
        # Check for entry signal
        if (current_price < current_bb_lower and 
            current_stoch_k < stoch_oversold and 
            near_ob):
            direction = "BULLISH"
            reason = (f"BB Oversold (Price ${current_price:.2f} < BB Lower ${current_bb_lower:.2f}) + "
                     f"Stochastic K={current_stoch_k:.1f} (<{stoch_oversold}) + OB Zone Confirmed")
            
            # SL: 2 ATR below entry
            stop_loss = current_price - (current_atr * 2)
            # TP: 2:1 risk reward
            take_profit = current_price + (current_atr * 4)
        
        # Check for exit signal
        elif current_price > current_bb_upper or current_stoch_k > stoch_overbought:
            direction = "FLAT"
            if current_price > current_bb_upper:
                reason = f"BB Overbought (Price ${current_price:.2f} > BB Upper ${current_bb_upper:.2f})"
            else:
                reason = f"Stochastic Overbought (K={current_stoch_k:.1f} >{stoch_overbought})"
        
        # Build signal dict
        signal_dict = None
        if direction:
            signal_dict = {
                "direction": direction,
                "entry_price": float(current_price),
                "stop_loss": float(stop_loss) if stop_loss else None,
                "take_profit": float(take_profit) if take_profit else None,
                "risk_reward": 2.0 if stop_loss and take_profit else None,
                "reason": reason,
                "metadata": {
                    "bb_sma": float(current_bb_sma),
                    "bb_upper": float(current_bb_upper),
                    "bb_lower": float(current_bb_lower),
                    "stoch_k": float(current_stoch_k),
                    "stoch_d": float(current_stoch_d),
                    "atr": float(current_atr),
                    "near_ob": near_ob,
                    "ob_count": len(recent_ob),
                    "signal_timestamp": str(data.index[-1])
                }
            }
        
        return entries, exits, signal_dict
        
    except Exception as e:
        logger.error(f"Error in BB_Stochastic_OB strategy: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, None


# For direct testing
if __name__ == "__main__":
    import yfinance as yf
    
    # Test with Yahoo Finance data
    ticker = yf.Ticker("GC=F")
    data = ticker.history(start="2026-03-02", end="2026-03-18", interval="15m")
    
    # Rename columns to match expected format
    data = data.rename(columns={
        'Open': 'open',
        'High': 'high', 
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    })
    
    entries, exits, signal = strategy(data)
    
    print("="*60)
    print("BB Stochastic Order Block Strategy Test")
    print("="*60)
    print(f"\nCurrent Signal: {signal['direction'] if signal else 'NONE'}")
    if signal:
        print(f"Entry Price: ${signal['entry_price']:.2f}")
        print(f"Stop Loss: ${signal['stop_loss']:.2f}" if signal['stop_loss'] else "Stop Loss: N/A")
        print(f"Take Profit: ${signal['take_profit']:.2f}" if signal['take_profit'] else "Take Profit: N/A")
        print(f"Reason: {signal['reason']}")
        print(f"\nIndicators:")
        print(f"  BB Lower: ${signal['metadata']['bb_lower']:.2f}")
        print(f"  BB Upper: ${signal['metadata']['bb_upper']:.2f}")
        print(f"  Stochastic K: {signal['metadata']['stoch_k']:.1f}")
        print(f"  Stochastic D: {signal['metadata']['stoch_d']:.1f}")
        print(f"  ATR: ${signal['metadata']['atr']:.2f}")
        print(f"  Near OB Zone: {signal['metadata']['near_ob']}")
