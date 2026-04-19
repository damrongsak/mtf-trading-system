# Skill: Institutional Gamma & Liquidity Intelligence

**Category:** Strategy & Risk
**Version:** 1.0
**Target Asset:** XAU/USD (Gold)

## 1. Overview
This skill enables the agent to analyze CME Group Options Open Interest (OI) and Global Exposure (GEX) to map institutional "hidden" price levels. It identifies where Market Makers are forced to hedge, creating powerful support/resistance walls and volatility regimes.

## 2. Capabilities
- **Regime Detection:** Identify `POSITIVE_GAMMA` (Stable/Mean Reverting) vs `NEGATIVE_GAMMA` (Volatile/Trending) states.
- **Institutional Mapping:** Locate the **Gamma Flip**, **Call Wall**, **Put Wall**, and **Max Pain**.
- **Execution Confluence:** Cross-reference SMC technical setups with institutional liquidity clusters.
- **Risk Calibration:** Recommend position sizing based on the volatility regime.

## 3. Logic & Decision Rules

### A. The Gamma Flip (Boundary)
- **Above Flip:** Market is in "mean reversion" mode. Fades of extremes are higher probability.
- **Below Flip:** Market is in "volatility" mode. Trend following and momentum setups are preferred. High risk of rapid cascades.

### B. The Walls (Support/Resistance)
- **Call Wall:** The absolute ceiling. Avoid buying into this level; look for reversals.
- **Put Wall:** The absolute floor. Avoid selling into this level; look for reversals.
- **Max Pain:** The "magnetic" price level. Price tends to drift toward this as OpEx (Option Expiry) approaches.

### C. Risk Multipliers
- **Positive Gamma:** Normal Risk (1.0x).
- **Negative Gamma:** Reduced Risk (0.5x) due to increased tail-risk and slippage.

## 4. Usage Instructions
Agent should use the `open_interest` tool to fetch raw data, then apply the logic above to provide a briefing.

### Example Commands:
- "Check institutional liquidity for Gold"
- "Are there any gamma walls near 2450?"
- "Evaluate current risk based on GEX regime"

## 5. Metadata
- **Tools Required:** `open_interest`
- **Reference Docs:** `references/gamma_theory.md`
- **Analysis Script:** `scripts/analyze_gamma.py`
