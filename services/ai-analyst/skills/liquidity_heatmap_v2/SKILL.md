---
name: liquidity_heatmap_v2
description: Advanced spatial analysis combining SMC Order Blocks with Options-based Liquidity Heatmaps to find high-probability reversal zones.
version: 1.0.0
author: Antigravity-AI
---

# Liquidity Heatmap v2 Skill

## 🎯 Goal
Identify "Confluence Zones" where technical SMC structures (Order Blocks, FVG) overlap with high-density Gamma/Option walls.

## 🛠️ Tools Required
- `liquidity_heatmap`: To fetch Gamma-based liquidity density and Max Pain.
- `smc_technical_analysis`: To identify Order Blocks (OB) and Fair Value Gaps (FVG).
- `get_market_context`: For current trend and ATR context.

## 📋 Instructions
1.  **Analyze Technical Structure**: Call `smc_technical_analysis` to identify the nearest H1/H4 Order Blocks and FVG.
2.  **Fetch Liquidity Data**: Call `liquidity_heatmap` for XAUUSD.
3.  **Identify Confluence Zones**:
    - Look for areas where a **Support/Resistance (Put/Call Wall)** with >70% density overlaps with an **SMC Order Block**.
    - Check if **Max Pain** aligns with a major Liquidity Gap or a "Magnet" target.
4.  **Execute Bias Audit**:
    - If price is below an OB + Put Wall (High Density), prioritize Longs (Bullish Reversal).
    - If price is above an OB + Call Wall (High Density), prioritize Shorts (Bearish Reversal).
5.  **Output**:
    - **Primary Confluence Zone**: [Strike Price] - [SMC Structure].
    - **Rejection Probability**: High/Medium/Low based on density + structure age.
    - **Recommended Action**: Entry/Exit logic relative to the zone.

## 🔗 References
Check `references/confluence_methodology.md` for scoring weights between SMC and Heatmap data.
