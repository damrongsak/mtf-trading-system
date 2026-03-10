---
name: sentiment_analyzer
description: Aggregates and analyzes market sentiment from multi-source data (Economic, Social, and Institutional).
version: 1.0.0
author: Antigravity-AI
---

# Sentiment Analyzer Skill

## 🎯 Goal
Provide a comprehensive sentiment breakdown for a given financial instrument (default: XAUUSD) by synthesizing disparate data sources into a single "Narrative Bias" score.

## 🛠️ Tools Required
- `WebReaderTool`: To scrape institutional reports or high-authority news.
- `GoogleSearchTool`: To find current sentiment drivers.
- `PythonInterpreterTool`: For computing weighted sentiment scores.
- `InternalSentimentService` (Optional/Contextual): For proprietary internal data.

## 📋 Instructions
1.  **Define Scope**: Identify the primary symbol and timeframe (Default is Intra-day/Daily).
2.  **Gather Data**:
    - Call `google_search` for queries like "Current market sentiment for [Symbol]" and "Institutional outlook on [Symbol]".
    - Call `web_reader` to extract details from high-impact headlines.
3.  **Analyze institutional Bias**:
    - Look for "Safe-haven demand", "Pivot expectations", or "Yield pressure" keywords.
    - Check for divergence between price action and retail sentiment (contrarian bias).
4.  **Synthesize**:
    - Compute a **Sentiment Score** from -10 (Extremely Bearish) to +10 (Extremely Bullish).
    - Map key drivers (e.g., "Geopolitical risk", "Hawkish Fed").
5.  **Output**:
    - **Narrative Bias**: One-sentence summary.
    - **Score**: X/10.
    - **Confidence**: High/Medium/Low based on data availability.

## 🔗 References
Check the `references/` directory for internal methodology and institutional weightings.
