#!/usr/bin/env python3
"""
Monte Carlo Simulation: SMC + ATR Volatility Strategy
=======================================================
Tests the proposed strategy with Monte Carlo simulation.

Configuration (from cTrader account):
- Initial NAV: $967.63 (cTrader 40816494)
- Risk per Trade: 1% ($9.68)
- Target RRR: 2:1
- Stop: 1.5 × ATR
- Max daily trades: 3

Author: Soda (AI Quant Engineer)
Date: 2026-03-02
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict
import json

# ============= CONFIG (FROM REAL DATA) =============
np.random.seed(42)

INITIAL_NAV = 967.63  # USD (cTrader 40816494)
RISK_PER_TRADE = 0.01  # 1%
TARGET_RRR = 2.0  # 2:1 reward:risk
AVG_TRADES_PER_WEEK = 3
WEEKS = 20
MONTE_CARLO_RUNS = 10000


# ============= MONTE CARLO ENGINE =============
def simulate_trade(win_rate: float, target_rrr: float = TARGET_RRR) -> Dict:
    """Simulate a single trade outcome."""
    is_win = np.random.random() < win_rate
    
    if is_win:
        pnl = target_rrr * RISK_PER_TRADE * 100
    else:
        pnl = -RISK_PER_TRADE * 100
    
    return {'win': is_win, 'pnl_percent': pnl}


def simulate_week(win_rate: float, num_trades: int = AVG_TRADES_PER_WEEK) -> float:
    """Simulate one week of trading."""
    weekly_pnl = 0.0
    for _ in range(num_trades):
        trade = simulate_trade(win_rate)
        weekly_pnl += trade['pnl_percent']
    return weekly_pnl


def simulate_path(win_rate: float, weeks: int = WEEKS) -> List[float]:
    """Simulate a complete trading path."""
    nav = INITIAL_NAV
    weekly_returns = []
    
    for week in range(weeks):
        weekly_pnl_pct = simulate_week(win_rate)
        nav = nav * (1 + weekly_pnl_pct / 100)
        weekly_returns.append(weekly_pnl_pct)
    
    return weekly_returns


def run_monte_carlo(win_rate: float, n_runs: int = MONTE_CARLO_RUNS) -> Dict:
    """Run full Monte Carlo simulation."""
    final_navs = []
    max_drawdowns = []
    weekly_returns = []
    
    for _ in range(n_runs):
        path = simulate_path(win_rate)
        
        # Final NAV
        final_nav = INITIAL_NAV
        for ret in path:
            final_nav *= (1 + ret / 100)
        final_navs.append(final_nav)
        
        # Max drawdown
        nav_series = [INITIAL_NAV]
        for ret in path:
            nav_series.append(nav_series[-1] * (1 + ret / 100))
        
        running_max = np.maximum.accumulate(nav_series)
        drawdown = (nav_series - running_max) / running_max
        max_drawdowns.append(np.min(drawdown) * 100)
        
        weekly_returns.extend(path)
    
    return {
        'final_nav': {
            'mean': float(np.mean(final_navs)),
            'median': float(np.median(final_navs)),
            'std': float(np.std(final_navs)),
            'percentile_5': float(np.percentile(final_navs, 5)),
            'percentile_95': float(np.percentile(final_navs, 95)),
            'min': float(np.min(final_navs)),
            'max': float(np.max(final_navs)),
        },
        'max_drawdown': {
            'mean': float(np.mean(max_drawdowns)),
            'median': float(np.median(max_drawdowns)),
            'percentile_95': float(np.percentile(max_drawdowns, 95)),
        },
        'weekly_return': {
            'mean': float(np.mean(weekly_returns)),
            'std': float(np.std(weekly_returns)),
            'sharpe_approx': float(np.mean(weekly_returns) / np.std(weekly_returns) * np.sqrt(52)),
        },
        'success_rate': {
            'profitable': float(sum(1 for nav in final_navs if nav > INITIAL_NAV) / len(final_navs) * 100),
            'doubled': float(sum(1 for nav in final_navs if nav >= INITIAL_NAV * 2) / len(final_navs) * 100),
            'survived': float(sum(1 for nav in final_navs if nav > INITIAL_NAV * 0.8) / len(final_navs) * 100),
        }
    }


def sensitivity_analysis() -> pd.DataFrame:
    """Test strategy across different win rates."""
    results = []
    
    for win_rate in np.arange(0.35, 0.70, 0.05):
        sim = run_monte_carlo(win_rate, n_runs=5000)
        
        results.append({
            'win_rate': f"{win_rate:.0%}",
            'expected_weekly_return': f"{sim['weekly_return']['mean']:.2f}%",
            'sharpe_approx': f"{sim['weekly_return']['sharpe_approx']:.2f}",
            'final_nav_mean': f"${sim['final_nav']['mean']:.2f}",
            'final_nav_5th': f"${sim['final_nav']['percentile_5']:.2f}",
            'max_dd_mean': f"{sim['max_drawdown']['mean']:.1f}%",
            'max_dd_95th': f"{sim['max_drawdown']['percentile_95']:.1f}%",
            'prob_profit': f"{sim['success_rate']['profitable']:.1f}%",
        })
    
    return pd.DataFrame(results)


def main():
    print("=" * 70)
    print("MONTE CARLO SIMULATION: SMC + ATR VOLATILITY STRATEGY")
    print("=" * 70)
    print(f"\nConfiguration (REAL DATA):")
    print(f"  Initial NAV:        ${INITIAL_NAV:.2f}")
    print(f"  Risk per Trade:    {RISK_PER_TRADE*100:.0f}% (${INITIAL_NAV * RISK_PER_TRADE:.2f})")
    print(f"  Target RRR:        {TARGET_RRR}:1")
    print(f"  Trades/Week:       {AVG_TRADES_PER_WEEK}")
    print(f"  Simulation:        {MONTE_CARLO_RUNS:,} runs × {WEEKS} weeks")
    print()
    
    # Scenario 1: 50%
    print("-" * 70)
    print("SCENARIO 1: WIN RATE = 50%")
    print("-" * 70)
    sim = run_monte_carlo(0.50)
    print(f"\nFinal NAV: Mean=${sim['final_nav']['mean']:.2f}, Median=${sim['final_nav']['median']:.2f}")
    print(f"5th %ile: ${sim['final_nav']['percentile_5']:.2f}, 95th %ile: ${sim['final_nav']['percentile_95']:.2f}")
    print(f"Max DD (mean): {sim['max_drawdown']['mean']:.1f}%, 95th: {sim['max_drawdown']['percentile_95']:.1f}%")
    print(f"Sharpe: {sim['weekly_return']['sharpe_approx']:.2f}")
    print(f"Prob Profit: {sim['success_rate']['profitable']:.1f}%")
    
    # Scenario 2: 55%
    print("\n" + "-" * 70)
    print("SCENARIO 2: WIN RATE = 55%")
    print("-" * 70)
    sim = run_monte_carlo(0.55)
    print(f"\nFinal NAV: Mean=${sim['final_nav']['mean']:.2f}, Median=${sim['final_nav']['median']:.2f}")
    print(f"5th %ile: ${sim['final_nav']['percentile_5']:.2f}, 95th %ile: ${sim['final_nav']['percentile_95']:.2f}")
    print(f"Max DD (mean): {sim['max_drawdown']['mean']:.1f}%, 95th: {sim['max_drawdown']['percentile_95']:.1f}%")
    print(f"Sharpe: {sim['weekly_return']['sharpe_approx']:.2f}")
    print(f"Prob Profit: {sim['success_rate']['profitable']:.1f}%")
    
    # Scenario 3: 60%
    print("\n" + "-" * 70)
    print("SCENARIO 3: WIN RATE = 60%")
    print("-" * 70)
    sim = run_monte_carlo(0.60)
    print(f"\nFinal NAV: Mean=${sim['final_nav']['mean']:.2f}, Median=${sim['final_nav']['median']:.2f}")
    print(f"5th %ile: ${sim['final_nav']['percentile_5']:.2f}, 95th %ile: ${sim['final_nav']['percentile_95']:.2f}")
    print(f"Max DD (mean): {sim['max_drawdown']['mean']:.1f}%, 95th: {sim['max_drawdown']['percentile_95']:.1f}%")
    print(f"Sharpe: {sim['weekly_return']['sharpe_approx']:.2f}")
    print(f"Prob Profit: {sim['success_rate']['profitable']:.1f}%")
    
    # Sensitivity
    print("\n" + "=" * 70)
    print("SENSITIVITY ANALYSIS")
    print("=" * 70)
    df = sensitivity_analysis()
    print("\n" + df.to_string(index=False))
    
    # Save JSON
    output = {
        'config': {
            'initial_nav': INITIAL_NAV,
            'risk_per_trade': RISK_PER_TRADE,
            'target_rrr': TARGET_RRR,
            'trades_per_week': AVG_TRADES_PER_WEEK,
            'weeks': WEEKS,
            'monte_carlo_runs': MONTE_CARLO_RUNS,
        },
        'scenario_50pct': run_monte_carlo(0.50),
        'scenario_55pct': run_monte_carlo(0.55),
        'scenario_60pct': run_monte_carlo(0.60),
    }
    
    with open('/home/dan/.openclaw/workspace/memory/monte_carlo_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=float)
    
    print("\n📁 Results saved to: memory/monte_carlo_results.json")


if __name__ == "__main__":
    main()
