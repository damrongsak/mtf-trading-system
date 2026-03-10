---
name: market_volatility_analyzer
description: Advanced volatility analysis for financial instruments, covering Historical Volatility (HV), ATR, and Regime detection.
version: 1.0.0
author: Antigravity-AI
---

# Market Volatility Analyzer

This skill provides the mechanical and statistical framework for analyzing price volatility across multiple timeframes.

## 🎯 Goal
Identify the current "Volatility Regime" (Low, Normal, Spiking, Elevated) to determine appropriate stop-loss placement and position sizing.

## 🛠️ Components
- **Instructions**: Contained in this `SKILL.md`.
- **Scripts**: `scripts/calculate_volatility.py` for HV and ADR calculations.
- **References**: `references/VOLATILITY_REFERENCE.md` for interpretation rules.
- **Assets**: `assets/report_template.json` for standardized analyst reports.

## 📋 Instructions
1.  **Gather OHLCV Data**: Use `GetMarketContextTool` to fetch the last 100 periods of data for the symbol.
2.  **Calculate HV**: 
    - Execute `scripts/calculate_volatility.py` using `PythonInterpreterTool` with the gathered data.
    - Calculate 20-period and 60-period Historical Volatility.
3.  **Determine Regime**: 
    - Compare current HV20 to its 60-period average.
    - Reference `references/VOLATILITY_REFERENCE.md` for mapping the ratio to a regime name.
4.  **Stop-Loss Multiplier**:
    - Use ATR x 2.5 for trending markets, ATR x 1.5 for low-volatility compression.
5.  **Output**:
    - Use the structured JSON in `assets/report_template.json` to format the final finding.

## ⚠️ Safety
Do not use this skill to justify increasing risk beyond the 1% Fund Limit defined in the institutional risk engine.
