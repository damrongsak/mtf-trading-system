#!/usr/bin/env python3
"""
Backtest: SMC + ATR Volatility Strategy (Relaxed)
=================================================
More signals = better statistics.

Date: 2026-03-Author: Soda
02
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import json

# ============= CONFIG =============
DB_URL = "postgresql://trader:trader@localhost:5432/mtf_db"
SYMBOL = "XAUUSD"
TIMEFRAME = "M15"

# Relaxed strategy params
ATR_PERIOD = 14
EMA_PERIOD = 20  # Shorter EMA for more signals
RISK_PER_TRADE = 0.01
RRR_TARGET = 2.0
ATR_STOP_MULTIPLIER = 1.5


def load_data() -> pd.DataFrame:
    engine = create_engine(DB_URL)
    query = """
    SELECT c.timestamp, c.open, c.high, c.low, c.close, c.volume
    FROM candles c
    JOIN market_symbols m ON c.market_symbol_id = m.id
    WHERE m.symbol = %s AND c.timeframe = %s
    ORDER BY c.timestamp ASC
    """
    df = pd.read_sql(query, engine, params=(SYMBOL, TIMEFRAME))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"Loaded {len(df)} candles ({df['timestamp'].min()} to {df['timestamp'].max()})")
    return df


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df['ema'] = df['close'].ewm(span=EMA_PERIOD, adjust=False).mean()
    
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(window=ATR_PERIOD).mean()
    
    return df


def find_smc_signals(df: pd.DataFrame) -> pd.DataFrame:
    # Trend
    df['trend_up'] = df['close'] > df['ema']
    df['trend_down'] = df['close'] < df['ema']
    
    # FVG - simplified
    df['fvg_bullish'] = (df['low'].shift(1) > df['high'].shift(2))
    df['fvg_bearish'] = (df['high'].shift(1) < df['low'].shift(2))
    
    # Simple momentum
    df['momentum_up'] = df['close'] > df['close'].shift(2)
    df['momentum_down'] = df['close'] < df['close'].shift(2)
    
    # Combined (relaxed)
    df['signal_long'] = df['trend_up'] & df['fvg_bullish'] & df['momentum_up']
    df['signal_short'] = df['trend_down'] & df['fvg_bearish'] & df['momentum_down']
    
    return df


def run_backtest(df: pd.DataFrame) -> dict:
    trades = []
    position = None
    entry_price = None
    entry_atr = None
    stop_loss = None
    take_profit = None
    
    initial_balance = 10000
    balance = initial_balance
    
    for i in range(30, len(df)):
        row = df.iloc[i]
        
        if pd.isna(row['atr']) or pd.isna(row['ema']):
            continue
            
        # Entry
        if position is None:
            if row['signal_long']:
                position = 'long'
                entry_price = row['close']
                entry_atr = row['atr']
                stop_loss = entry_price - (entry_atr * ATR_STOP_MULTIPLIER)
                take_profit = entry_price + (entry_atr * ATR_STOP_MULTIPLIER * RRR_TARGET)
                
            elif row['signal_short']:
                position = 'short'
                entry_price = row['close']
                entry_atr = row['atr']
                stop_loss = entry_price + (entry_atr * ATR_STOP_MULTIPLIER)
                take_profit = entry_price - (entry_atr * ATR_STOP_MULTIPLIER * RRR_TARGET)
        
        # Exit
        elif position == 'long':
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                balance *= (1 + pnl / 100)
                trades.append({'type': 'long', 'pnl': pnl, 'exit': 'SL'})
                position = None
            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                balance *= (1 + pnl / 100)
                trades.append({'type': 'long', 'pnl': pnl, 'exit': 'TP'})
                position = None
                
        elif position == 'short':
            if row['high'] >= stop_loss:
                pnl = (entry_price - stop_loss) / entry_price * 100
                balance *= (1 + pnl / 100)
                trades.append({'type': 'short', 'pnl': pnl, 'exit': 'SL'})
                position = None
            elif row['low'] <= take_profit:
                pnl = (entry_price - take_profit) / entry_price * 100
                balance *= (1 + pnl / 100)
                trades.append({'type': 'short', 'pnl': pnl, 'exit': 'TP'})
                position = None
    
    if not trades:
        return {
            'total_trades': 0, 'win_rate': 0, 'avg_win': 0,
            'avg_loss': 0, 'avg_rrr': 0, 'final_balance': balance,
            'return_pct': (balance - initial_balance) / initial_balance * 100,
            'trades': [],
        }
    
    wins = [t['pnl'] for t in trades if t['pnl'] > 0]
    losses = [t['pnl'] for t in trades if t['pnl'] <= 0]
    
    return {
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_win': np.mean(wins) if wins else 0,
        'avg_loss': np.mean(losses) if losses else 0,
        'avg_rrr': abs(np.mean(wins) / np.mean(losses)) if losses and wins else 0,
        'final_balance': balance,
        'return_pct': (balance - initial_balance) / initial_balance * 100,
        'trades': trades,
    }


def main():
    print("=" * 70)
    print("BACKTEST: SMC + ATR (RELAXED)")
    print("=" * 70)
    
    df = load_data()
    df = calculate_indicators(df)
    df = find_smc_signals(df)
    
    long_sig = df['signal_long'].sum()
    short_sig = df['signal_short'].sum()
    print(f"Signals: Long={long_sig}, Short={short_sig}")
    
    results = run_backtest(df)
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Trades: {results['total_trades']} | Win Rate: {results['win_rate']:.1f}%")
    print(f"Avg Win: {results['avg_win']:.2f}% | Avg Loss: {results['avg_loss']:.2f}%")
    print(f"Avg RRR: {results['avg_rrr']:.2f}:1")
    print(f"Return: {results['return_pct']:.2f}% | Final: ${results['final_balance']:.2f}")
    
    # Trade breakdown
    print(f"\nTrade breakdown:")
    for t in results['trades']:
        print(f"  {t['type']:5s} | {t['pnl']:+6.2f}% | {t['exit']}")
    
    # Save
    output = {
        'config': {'symbol': SYMBOL, 'timeframe': TIMEFRAME, 'ema_period': EMA_PERIOD,
                   'atr_period': ATR_PERIOD, 'rrr_target': RRR_TARGET, 'atr_stop_mult': ATR_STOP_MULTIPLIER},
        'results': results,
    }
    with open('/home/dan/.openclaw/workspace/memory/backtest_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=float)
    
    print("\n📁 Saved to memory/backtest_results.json")


if __name__ == "__main__":
    main()
