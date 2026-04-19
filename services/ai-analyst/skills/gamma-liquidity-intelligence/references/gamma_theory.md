# Theory: Institutional Liquidity & Gamma Exposure (GEX)

## 1. What is Gamma?
Gamma measures the rate of change in an option's **Delta** relative to the underlying price. For institutional analysis, we focus on **Dealer Gamma**—the net exposure of Market Makers who sell options to the public.

## 2. Market Maker Hedging
Market Makers must remain "Delta Neutral." To do this, they buy or sell the underlying asset (Gold Futures) as price moves:
- **When they are "Long Gamma" (Positive):** They sell into rallies and buy into dips. This **dampens** volatility (Mean Reversion).
- **When they are "Short Gamma" (Negative):** They must buy into rallies and sell into dips. This **accelerates** volatility (Trending/Crashing).

## 3. Key Institutional Levels

### The Gamma Flip
The price level where Dealer Gamma switches from Positive to Negative. It is the most important "regime boundary" in modern quantitative trading.

### Call Wall
The strike price with the largest net positive Gamma. Market Makers have a large "Short Call" position here, forcing them to sell futures as price approaches, creating a massive resistance ceiling.

### Put Wall
The strike price with the largest net negative Gamma (from the public's perspective, Dealers are Long Puts). It acts as a primary floor where Dealers must buy futures to hedge, creating strong support.

### Max Pain
The strike price where the most options contracts (both calls and puts) would expire worthless. It acts as a "magnet" because it is the point of maximum profit for option sellers (Dealers).

## 4. Application to MTF Olympus
- **High Confluence:** A technical Order Block (OB) sitting exactly at a Call Wall is a "Tier 1" short setup.
- **Regime Filter:** Do not use mean-reversion bots (Grid bots) when price is below the Gamma Flip.
- **Targeting:** Use Max Pain as a take-profit target for counter-trend trades.
