#!/usr/bin/env python3
"""
XAUUSD SMC Signal Monitor
=========================
Monitors XAUUSD and sends signals via Olympus Telegram.

Author: Soda
Date: 2026-03-02
"""

import requests
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine

# ============= CONFIG =============
DB_URL = "postgresql://trader:trader@localhost:5432/mtf_db"
API_URL = "http://localhost:8000"
USERNAME = "trader1"
PASSWORD = "password123"
SYMBOL = "XAUUSD"
TIMEFRAME = "M15"

# Strategy params
EMA_PERIOD = 20
ATR_PERIOD = 14
CHECK_INTERVAL = 900  # 15 minutes

# Auth (will refresh)
token = None
user_id = None


def get_auth():
    """Get fresh auth token."""
    global token, user_id
    resp = requests.post(
        f"{API_URL}/api/v1/auth/token",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    data = resp.json()
    token = data['auth']['access_token']
    user_id = data['data']['id']
    return token, user_id


def send_telegram(message: str):
    """Send message via Olympus Telegram."""
    if not token:
        get_auth()
    
    resp = requests.post(
        f"{API_URL}/api/v1/telegram/send",
        json={"message": message},
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp.json()


def get_latest_price() -> dict:
    """Get latest XAUUSD price from DB."""
    engine = create_engine(DB_URL)
    query = """
    SELECT c.timestamp, c.open, c.high, c.low, c.close, c.volume
    FROM candles c
    JOIN market_symbols m ON c.market_symbol_id = m.id
    WHERE m.symbol = %s AND c.timeframe = %s
    ORDER BY c.timestamp DESC
    LIMIT 1
    """
    df = pd.read_sql(query, engine, params=(SYMBOL, TIMEFRAME))
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def get_recent_candles(n: int = 50) -> pd.DataFrame:
    """Get recent candles for analysis."""
    engine = create_engine(DB_URL)
    query = """
    SELECT c.timestamp, c.open, c.high, c.low, c.close, c.volume
    FROM candles c
    JOIN market_symbols m ON c.market_symbol_id = m.id
    WHERE m.symbol = %s AND c.timeframe = %s
    ORDER BY c.timestamp DESC
    LIMIT %s
    """
    df = pd.read_sql(query, engine, params=(SYMBOL, TIMEFRAME, n))
    df = df.sort_values('timestamp')
    return df


def analyze_signal(df: pd.DataFrame) -> dict:
    """Analyze for SMC signal."""
    if len(df) < 30:
        return {'signal': None, 'reason': 'Insufficient data'}
    
    # Calculate indicators
    df = df.copy()
    df['ema'] = df['close'].ewm(span=EMA_PERIOD, adjust=False).mean()
    
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['atr'] = ranges.max(axis=1).rolling(window=ATR_PERIOD).mean()
    
    latest = df.iloc[-1]
    
    # Skip if no ATR
    if pd.isna(latest['atr']) or pd.isna(latest['ema']):
        return {'signal': None, 'reason': 'No indicators'}
    
    # Trend
    trend_up = latest['close'] > latest['ema']
    trend_down = latest['close'] < latest['ema']
    
    # FVG
    fvg_bullish = latest['low'] > df.iloc[-3]['high'] if len(df) >= 3 else False
    fvg_bearish = latest['high'] < df.iloc[-3]['low'] if len(df) >= 3 else False
    
    # Momentum
    momentum_up = latest['close'] > df.iloc[-3]['close'] if len(df) >= 3 else False
    momentum_down = latest['close'] < df.iloc[-3]['close'] if len(df) >= 3 else False
    
    # Signals
    signal_long = trend_up and fvg_bullish and momentum_up
    signal_short = trend_down and fvg_bearish and momentum_down
    
    if signal_long:
        entry = latest['close']
        sl = entry - (latest['atr'] * 2.0)
        tp = entry + (latest['atr'] * 2.0 * 2.0)
        return {
            'signal': 'LONG',
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'atr': latest['atr'],
            'ema': latest['ema'],
            'trend': 'up'
        }
    elif signal_short:
        entry = latest['close']
        sl = entry + (latest['atr'] * 2.0)
        tp = entry - (latest['atr'] * 2.0 * 2.0)
        return {
            'signal': 'SHORT',
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'atr': latest['atr'],
            'ema': latest['ema'],
            'trend': 'down'
        }
    
    return {'signal': None, 'reason': 'No setup'}


def format_signal(msg: dict, price: float) -> str:
    """Format signal message."""
    direction = "🟢 LONG" if msg['signal'] == 'LONG' else "🔴 SHORT"
    
    return f"""
{direction} XAUUSD {TIMEFRAME}

Entry: {msg['entry']:.2f}
SL:    {msg['sl']:.2f}
TP:    {msg['tp']:.2f}

📊 Stats:
• EMA{EMA_PERIOD}: {msg['ema']:.2f}
• ATR{ATR_PERIOD}: {msg['atr']:.2f}
• Trend: {msg['trend']}

⏰ {datetime.now().strftime('%H:%M %d/%m')}
"""


def main():
    print("=" * 60)
    print("XAUUSD SMC Monitor - Starting...")
    print("=" * 60)
    
    # Initial auth
    get_auth()
    print(f"✅ Auth: {user_id}")
    
    # Get initial data
    price = get_latest_price()
    print(f"📊 Current price: {price['close']}")
    
    # Analyze
    df = get_recent_candles(50)
    analysis = analyze_signal(df)
    
    print(f"\n📈 Analysis: {analysis}")
    
    if analysis['signal']:
        # Send signal
        message = format_signal(analysis, price['close'])
        result = send_telegram(message)
        print(f"\n✅ Signal sent to Telegram!")
        print(f"   Chat ID: {result.get('chat_id')}")
        print(f"\n{message}")
    else:
        msg = f"🔔 XAUUSD Monitor\n\nNo setup currently.\nPrice: {price['close']}\n\nReason: {analysis['reason']}"
        send_telegram(msg)
        print(f"\nℹ️ No signal - {analysis['reason']}")
    
    print("\n✅ Monitor cycle complete")


if __name__ == "__main__":
    main()
