# Sunday Quant Scientist Newsletter

Get every Sunday issue of the Quant Scientist newsletter by [joining the list](https://learn.quantscience.io/quant-scientist-newsletter-register-9614).

## What's Inside
- Each `QS###-*` directory is a self-contained walkthrough referenced in the matching newsletter issue.
- Most folders contain a single `01_*.py` script (or, for `QS001`, a `.bash` cheat sheet) plus any images/outputs the article mentions.
- `requirements.txt` aggregates everything used across all issues. Install only what you need for the scripts you plan to run.
- The `temp/` directory holds experiments and drafts that have not yet been turned into newsletter-ready content.

## Quick Start
```bash
# 1. Create a virtual environment (Python 3.10+ recommended)
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies (installs everything; feel free to trim for a single issue)
pip install -r requirements.txt

# 3. Run any issue script
python QS010-relative-strength-index/01_rsi.py
```

Many scripts fetch data from public APIs (e.g., OpenBB, Yahoo Finance, QuantStats) and will download charts, CSVs, or HTML tear sheets into their respective folders. Check each script for optional API keys or parameters you may want to tweak before running.

## Repository Layout
- `QS###-name/` – Production-ready newsletter examples, numbered to match the Sunday Quant Scientist issues (missing numbers indicate unpublished or future topics).
- `temp/` – Scratch work, prototypes, and supporting material that may change without notice.
- `requirements.txt` – Superset dependency list for every example.
- `README.md` – You are here.

## Issue Index
| Issue | Folder | Focus |
| --- | --- | --- |
| QS001 | `QS001-openbb-financial-data` | OpenBB Terminal command cheat sheet for replicating a $29k data terminal |
| QS002 | `QS002-automate-trades` | Automate trade sizing with the OpenBB SDK plus Riskfolio optimizations |
| QS003 | `QS003-stock-screener-openbb-sdk` | Build and export a custom stock screener with the OpenBB SDK |
| QS004 | `QS004-avoid-algo-trading-mistakes` | Avoid common algo mistakes with exponential moving averages |
| QS005 | `QS005-pytimetk-first-look` | First look at pytimetk for fast time-series plotting |
| QS006 | `QS006-anomaly-buy-sell` | Detect buy/sell anomalies with pytimetk's STL decomposition |
| QS007 | `QS007-ML-in-finance` | Machine-learning driven SPY trend detection |
| QS008 | `QS008-fast-fourier-transform` | Fast Fourier Transform signal extraction for price data |
| QS009 | `QS009-average-true-range` | Average True Range (ATR) indicator walkthrough |
| QS010 | `QS010-relative-strength-index` | Relative Strength Index (RSI) indicator build |
| QS011 | `QS011-skfolio-risk-parity` | Risk-parity allocation with the skfolio library |
| QS012 | `QS012-pytimetk-finance-module` | pytimetk finance module exploration and utilities |
| QS013 | `QS013-macd` | Moving Average Convergence Divergence (MACD) indicator |
| QS014 | `QS014-riskfolio` | Multi-asset allocation with Riskfolio-Lib |
| QS015 | `QS015-alphalens` | Factor analysis using Alphalens Reloaded |
| QS016 | `QS016-nancy-pelosi-portfolio` | Nancy Pelosi portfolio replication and risk stats |
| QS017 | `QS017-quantstats-tearsheets` | Generate QuantStats HTML tear sheets |
| QS018 | `QS018-polars` | Data wrangling for trading workflows using Polars |
| QS019 | `QS019-correlation` | Correlation matrices and heatmaps for asset selection |
| QS020 | `QS020-ffn` | Using the `ffn` library for backtesting primitives |
| QS021 | `QS021-mplfinance` | Candlestick charting with `mplfinance` |
| QS022 | `QS022-hrp` | Hierarchical Risk Parity optimizer example |
| QS023 | `QS023-kmeans` | K-Means clustering applied to market regimes |
| QS024 | `QS024-downside-deviation` | Comparing downside deviation against traditional volatility |
| QS025 | `QS025-autoencoders` | Autoencoder-based anomaly detection for trading signals |
| QS026 | `QS026-markov` | Markov models applied to regime detection |
| QS027 | `QS027-pcr` | Principal Component Regression (PCR) for factor modeling |
| QS028 | `QS028-flow-effects` | Strategy based on flow effects delivering triple-digit returns |
| QS029 | `QS029-buffett` | Capture fundamental ratios Warren Buffett tracks |
| QS030 | `QS030-omega` | Responsible trading metrics with the Omega ratio |
| QS031 | `QS031-kelly` | Position sizing using the Kelly criterion |
| QS032 | `QS032-information-ratio` | Evaluate trading skill with the Information Ratio |
| QS034 | `QS034-optimize-exits` | Optimize exits to lock in gains |
| QS035 | `QS035-autocorrelation` | Use autocorrelation to uncover trends |
| QS037 | `QS037-tensortrade` | Reinforcement-learning strategies with TensorTrade |
| QS038 | `QS038-fast-fourier-transform` | Alternate FFT workflow for denoising prices |
| QS039 | `QS039-graph-optimization` | Graph-based optimization to improve Sharpe ratios |
| QS040 | `QS040-cvar` | Conditional Value at Risk (CVaR) capital protection |
| QS041 | `QS041-hurst-exponent` | Determine trend vs. mean-reversion with the Hurst exponent |
| QS043 | `QS043-3-day-pullback` | Three-day pullback strategy with ~77% win rate |
| QS044 | `QS044-tail-ratio` | Tail ratio and related risk metrics for strategy vetting |
| QS045 | `QS045-mean-reversion` | Mean-reversion backtest and visualization |
| QS046 | `QS046-download-free-market-data` | Download free market data programmatically |
| QS047 | `QS047-skew-kurtosis` | Measure fat-tailed returns via skew and kurtosis |
| QS048 | `QS048-dollar-neutral` | Build a dollar-neutral long/short portfolio |

> ℹ️ Some issue numbers (e.g., QS033, QS036, QS042) are missing intentionally—they correspond to drafts or upcoming releases.

## Need Help?
Reach out via the newsletter reply-to address or drop an issue/PR with questions, additions, or corrections.
