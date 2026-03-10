# Sentiment Analysis Methodology (v1.0)

To achieve institutional-grade sentiment scores, use the following weighting system:

## 1. Data Source Weighting
| Source | Weight | Description |
| :--- | :--- | :--- |
| Institutional Reports (e.g., Goldman, JP Morgan) | 40% | Derived from WebReader extraction of public outlooks. |
| Economic Data Surprise (vs Forecast) | 30% | Macro impact of CPI/NFP data. |
| News Sentiment (Headlines) | 20% | Breaking geopolitics and sector-specific news. |
| Retail Sentiment (e.g., Sentiment Indexes) | 10% | Used as a contrarian indicator in extreme readings. |

## 2. Narrative Classification
- **Risk On**: Improving PMI, Fed Pivot signals, Geopolitical de-escalation.
- **Risk Off**: Safe-haven demand (Gold/USDCAD up), Inflation spikes, War threats.

## 3. Score Calibration
- **+10**: Unanimous bullish institutional backing + Risk On environment.
- **0**: Perfect equilibrium or conflicting high-impact data.
- **-10**: Unanimous bearish institutional backing + Risk Off flight to quality.
