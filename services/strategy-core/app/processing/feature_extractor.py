import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from app.indicators import (
    calculate_rsi, calculate_atr, calculate_macd, calculate_bbands, 
    calculate_ema, calculate_adx, detect_structure,
    detect_order_blocks, detect_fvg, detect_liquidity_sweeps
)

logger = logging.getLogger(__name__)

class FeatureExtractor:
    """
    Encapsulates the logic for calculating technical indicators and features
    from raw OHLCV data.
    """

    def extract_from_dataframe(self, df: pd.DataFrame, symbol: str = "UNKNOWN", timeframe: str = "UNKNOWN") -> Optional[Dict[str, Any]]:
        """
        Calculates all standard features for the provided DataFrame.
        Returns a dictionary formatted for the Alpha Stream.
        """
        if df.empty or len(df) < 50:
             return None

        # Sort ASC for calculation (handled by caller usually, but safe to ensure copy)
        # Using copy to avoid modifying original if passed by reference
        df = df.copy() # Ensure we don't mutate the passed DF
        
        # Calculations
        
        # 1. RSI (14)
        try:
            df['rsi_14'] = calculate_rsi(df['close'], window=14)
        except Exception as e:
            logger.debug(f"RSI calc failed for {symbol}: {e}")
            df['rsi_14'] = None
        
        # 2. SMA/EMA
        try:
            df['ema_9'] = calculate_ema(df['close'], span=9)
            df['ema_20'] = calculate_ema(df['close'], span=20)
            df['ema_50'] = calculate_ema(df['close'], span=50)
            df['ema_200'] = calculate_ema(df['close'], span=200)
        except Exception as e:
            logger.debug(f"EMA calc failed for {symbol}: {e}")

        # 3. ATR (14)
        try:
            df['atr_14'] = calculate_atr(df['high'], df['low'], df['close'], window=14)
        except Exception as e:
            logger.debug(f"ATR calc failed for {symbol}: {e}")
            df['atr_14'] = None
        
        # 4. Volatility (20)
        try:
            df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        except Exception as e:
             logger.debug(f"Volatility calc failed for {symbol}: {e}")

        # 5. MACD (12, 26, 9)
        try:
            macd_res = calculate_macd(df['close'], fast=12, slow=26, signal=9)
            df['macd'] = macd_res['macd']
            df['macd_signal'] = macd_res['signal']
            df['macd_hist'] = macd_res['hist']
        except Exception as e:
            logger.debug(f"MACD calc failed for {symbol}: {e}") 
            
        # 6. Bollinger Bands (20, 2.0)
        try:
            bb_res = calculate_bbands(df['close'], window=20, alpha=2.0)
            df['bb_upper'] = bb_res.upper
            df['bb_middle'] = bb_res.middle
            df['bb_lower'] = bb_res.lower
        except Exception as e:
            logger.debug(f"BB calc failed for {symbol}: {e}")

        # 7. ADX (14)
        try:
            adx_res = calculate_adx(df['high'], df['low'], df['close'], length=14)
            if adx_res is not None:
                 df['adx'] = adx_res['adx']
                 df['dmp'] = adx_res['dmp'] # DI+
                 df['dmn'] = adx_res['dmn'] # DI-
        except Exception as e:
            logger.debug(f"ADX calc failed for {symbol}: {e}")

        # 8. High/Low Logic (Donchian-like)
        try:
            df['high_20'] = df['high'].rolling(window=20).max()
            df['low_20'] = df['low'].rolling(window=20).min()
        except Exception as e:
             logger.debug(f"High/Low calc failed for {symbol}: {e}")

        # 9. SMC Structure (Swing High/Low)
        swing_high = None
        swing_low = None
        smc_data = {}
        
        try:
            # Calculate full structure
            structure = detect_structure(df, window=5) 
            
            # Get last confirmed labels for simple Swing metrics
            if structure['labels']:
                highs = [x for x in structure['labels'] if x['text'] in ['H', 'HH', 'LH']]
                lows = [x for x in structure['labels'] if x['text'] in ['L', 'LL', 'HL']]
                
                if highs:
                    swing_high = highs[-1]['price']
                if lows:
                    swing_low = lows[-1]['price']
                    
            # Package full objects
            smc_data = {
                "structure": structure,
                "order_blocks": detect_order_blocks(df),
                "fvgs": detect_fvg(df),
                "liquidity_sweeps": detect_liquidity_sweeps(df)
            }

        except Exception as e:
            logger.debug(f"SMC Structure calc failed for {symbol}: {e}")
            smc_data = {"error": str(e)}

        latest = df.iloc[-1]
        
        return {
            "type": "FEATURE",
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": latest['timestamp'],
            "close": float(latest['close']),
            "high": float(latest['high']),
            "low": float(latest['low']),
            
            # Indicators
            "rsi_14": self._safe_float(latest.get('rsi_14')),
            "atr_14": self._safe_float(latest.get('atr_14')),
            "ema_9": self._safe_float(latest.get('ema_9')),
            "ema_20": self._safe_float(latest.get('ema_20')),
            "ema_50": self._safe_float(latest.get('ema_50')),
            "ema_200": self._safe_float(latest.get('ema_200')),
            "volatility": self._safe_float(latest.get('volatility')),
            
            # MACD
            "macd": self._safe_float(latest.get('macd')),
            "macd_signal": self._safe_float(latest.get('macd_signal')),
            "macd_hist": self._safe_float(latest.get('macd_hist')),
            
            # BBands
            "bb_upper": self._safe_float(latest.get('bb_upper')),
            "bb_middle": self._safe_float(latest.get('bb_middle')),
            "bb_lower": self._safe_float(latest.get('bb_lower')),
            
            # ADX
            "adx": self._safe_float(latest.get('adx')),
            "di_plus": self._safe_float(latest.get('dmp')),
            "di_minus": self._safe_float(latest.get('dmn')),
            
            # High/Low
            "high_20": self._safe_float(latest.get('high_20')),
            "low_20": self._safe_float(latest.get('low_20')),
            "swing_high": swing_high,
            "swing_low": swing_low,
            
            # Full SMC Objects
            "smc": smc_data
        }

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        try:
            if pd.isna(val) or np.isinf(val):
                return None
            return float(val)
        except:
             return None
