# **Strategic Integration of CME Gold Open Interest Heatmaps: Quantitative Modeling and Pythonic Execution**

The global gold market represents a complex intersection of commodity demand, geopolitical risk, and macroeconomic sentiment, with the Chicago Mercantile Exchange (CME) COMEX futures serving as the primary venue for price discovery and institutional liquidity. Within this sophisticated ecosystem, open interest (OI) emerges not merely as a volume metric, but as a structural indicator of the total capital committed to the market.1 Unlike trading volume, which captures the transient flow of transactions within a discrete window, open interest quantifies the aggregate value of positions held overnight, offering a high-fidelity signal of market conviction and institutional positioning.3 The analysis of gold futures and options open interest, particularly when visualized through the CME QuikStrike Heatmap, provides quantitative traders with a "risk atlas" that identifies zones of high position density where price action is likely to stall, accelerate, or revert.5

## **Microstructure of Gold Open Interest and Price Dynamics**

Open interest in the COMEX gold futures market represents the total number of outstanding contracts that have not yet been settled by an offsetting trade, delivery, or exercise.1 The lifecycle of these contracts is governed by the four-way interaction of market participants. If a new buyer and a new seller enter a contract, open interest increases by one, signifying the entry of fresh capital.3 Conversely, if both parties close out existing positions, open interest decreases, indicating capital withdrawal.1 When a buyer opens a position while a seller closes an existing one, the open interest remains unchanged, suggesting a transfer of risk rather than a shift in total market size.6

For the systematic gold trader, the relationship between price movement and open interest changes provides the first layer of sentiment analysis.7 An increasing price accompanied by rising open interest is a classic bullish confirmation, as it suggests new long positions are being established.7 In contrast, a rally characterized by falling open interest often points to a "short-covering" phenomenon, where the price is driven higher by the exit of bears rather than the entry of bulls, often leading to a fragile trend that reverses once the buying pressure from short liquidation is exhausted.7 Research into gold futures volatility has demonstrated a potential negative influence of open interest on price fluctuations; when open interest is significant, it often acts as a stabilizing force, whereas low open interest environments are prone to higher volatility and erratic price gaps.9

| Price Trend | Open Interest Shift | Volume Momentum | Interpretation |
| :---- | :---- | :---- | :---- |
| Rising | Increasing | Increasing | Bullish Confirmation; Strong Trend |
| Rising | Decreasing | Increasing | Short Covering; Weak Trend |
| Falling | Increasing | Increasing | Bearish Conviction; Strong Trend |
| Falling | Decreasing | Decreasing | Long Unwinding; Weak Trend |
| Neutral | Increasing | Low | Accumulation; Potential Breakout |

1

## **The CME QuikStrike Heatmap: Visualizing the Gamma Landscape**

The CME QuikStrike Option Open Interest Heatmap is an advanced analytical tool that transforms the tabular data of the option chain into a spatial representation of market risk.11 By mapping the concentration of open interest across strikes and expirations, the heatmap reveals the "gravity" of the market.5 In the gold options market, these concentrations are critical because they dictate the hedging requirements of institutional dealers and market makers who facilitate the bulk of the liquidity.8

### **Structural Forces and the Pinning Phenomenon**

The concept of "pinning" is central to the utility of the heatmap. When a specific strike price accumulates a large volume of call or put options, it often becomes a natural magnet for the underlying gold price as expiration approaches.5 This phenomenon is driven by delta-neutral hedging adjustments. Dealers who have sold these options to the public are "short gamma." To remain neutral as the price of gold moves toward a high-OI strike, they must mechanically buy or sell the underlying futures contract, which effectively "pulls" the price toward the strike or suppresses its movement away from it.5

The heatmap provides an immediate visual of these position densities. A dense cluster on the heatmap signifies a zone where institutional players have strong incentives to defend a level, or where the mechanical hedging flows will likely stall the market.5 Conversely, if the price of gold breaks through a dense cluster, the reaction is often explosive. This occurs because moving past a heavily loaded strike abruptly changes the dealer's risk structure, forcing them to rapidly re-hedge in the direction of the breakout, thereby amplifying the move.5

### **Heatmap Mechanics and Filtering for Signal**

The QuikStrike interface allows for granular analysis of these structures through various view toggles.11 The "matrix" view displays a grid of expirations versus strikes, with color gradients (typically white to green) representing the magnitude of open interest.12 Traders can also view the "change" in open interest, which highlights where new bets are being placed over 1-day, 1-week, or 1-month periods.11

In the gold market, distinguishing between "Long Buildup" (rising OI and rising Implied Volatility) and "Short Buildup" (rising OI and falling Implied Volatility) is essential for decoding whether a "hot" strike on the heatmap represents aggressive hedging or speculative positioning.15 Furthermore, the heatmap allows traders to identify "gamma structure," where near-spot options shape the immediate trading environment.5 Dealers who are "long gamma" tend to stabilize prices, while "short gamma" environments are prone to volatility expansion.5

| Heatmap Metric | Visualization Logic | Quantitative Application |
| :---- | :---- | :---- |
| Absolute OI | Color intensity by magnitude | Identifies major structural support/resistance |
| OI Change | Diverging color scale (Red/Green) | Tracks shifts in sentiment and active repositioning |
| Column Heatmap | Vertical coloring by strike | Compares strike relative strength within an expiry |
| Matrix Heatmap | Two-dimensional color mapping | Analyzes risk distribution across time and price |

12

## **Theoretical Pillar: Max Pain and Institutional Incentives**

The Max Pain theory is a derivative of open interest analysis that identifies the strike price where the highest number of option contracts would expire worthless.8 This point represents the level of minimum payout for option writers (sellers) and maximum loss for option buyers.8 In the COMEX gold market, where institutional players such as bullion banks and hedge funds dominate the writing of options, the Max Pain price acts as a psychological and mechanical anchor for settlement.8

### **Calculation Methodology for Gold Options**

Determining the Max Pain point requires an exhaustive sum of the potential losses for both call and put writers across all available strikes.8 For a hypothetical settlement price ![][image1], the total "pain" is calculated as:

![][image2]  
Where ![][image3] and ![][image4] are the strike prices for calls and puts, respectively.18 By iterating this calculation across all possible settlement strikes, the quantitative trader identifies the strike that yields the minimum total pain.8

As the gold futures contract approaches its monthly expiration, the underlying price often gravitates toward this Max Pain point.8 This is not necessarily due to overt manipulation but rather a result of the collective hedging behavior of the institutional writing community, who benefit from most options expiring out-of-the-money.5 Identifying the Max Pain level allows traders to avoid buying options at strikes that are likely to be pinned and instead allows them to align their futures positioning with the likely direction of the magnetic pull of the settlement price.8

## **Sentiment Disaggregation: The Commitment of Traders (COT) Framework**

The analysis of total open interest is enriched by the Commodity Futures Trading Commission's (CFTC) Commitment of Traders (COT) report, which disaggregates the CME open interest data into specific participant categories.20 For gold, these reports provide a map of "who" is doing the buying and selling, allowing traders to distinguish between informed institutional flows and speculative retail noise.21

### **Participant Roles and Gold Market Conviction**

The legacy COT report and the more detailed disaggregated report categorize traders into four primary groups, each with a distinct relationship to gold price discovery.23

| Category | Typical Behavior | Significance for Gold Strategy |
| :---- | :---- | :---- |
| Commercials | Producers/Hedgers | Usually net-short; extreme buying signals a major bottom |
| Non-Commercials | Hedge Funds/Speculators | Trend-followers; large net-longs confirm current rally |
| Managed Money | Systematic CTAs | Momentum-driven; highly sensitive to technical breakouts |
| Non-Reportable | Small Retail Traders | Often wrong at extremes; used as a contrarian indicator |

21

In the gold market, the "Non-Commercials" (Large Speculators) are the most reactive to changes in fundamental and technical developments.22 A significant increase in their long positions often precedes a sustained rise in gold prices.22 However, when their positioning reaches historical extremes, it often marks the peak of a cycle.21 Successful quantitative strategies often combine these weekly COT signals with daily open interest heatmap data to time entries.22 For example, if COT indicates Managed Money is aggressively long, but the daily heatmap shows a massive concentration of call open interest just above the current price, the trader may wait for a "short-gamma" breakout through that cluster before entering, as the dealer hedging will accelerate the move.5

## **Quantitative Design: Systematic Python Architectures for Gold Trading**

Building a gold trading strategy based on open interest requires a robust data pipeline capable of retrieving, parsing, and analyzing CME COMEX data.25 Python, through its specialized libraries like Pandas and Plotly, provides the ideal environment for this development.27

### **Data Acquisition via CME DataMine API**

The foundation of the strategy is the programmatic retrieval of Volume and Open Interest (VOI) files from the CME DataMine API.25 These files provide the official, exchange-verified settlement figures for gold futures and options.30 The API requires authentication via OAuth 2.0 or Basic Auth and uses specific identifiers to filter for gold (Product Code: GC) and exchange (XCEC).25

The VOI data layout typically includes:

1. **Trade Date**: The official date of the session (YYYYMMDD).30  
2. **Product Description**: E.g., Gold Futures or Gold Options.30  
3. **Contract Year/Month**: Identifies the specific maturity of the future or option.30  
4. **Strike Price**: Critical for option heatmap and Max Pain calculations.30  
5. **Open Interest**: The primary variable for the structural analysis.30  
6. **Total Volume**: Used to validate the strength of the OI change.30

### **Automated Max Pain and Heatmap Logic**

Once the data is ingested, the system must compute the Max Pain level and visualize the risk map. The following Python logic provides a framework for these tasks, utilizing a vectorized approach to iterate through potential settlement strikes efficiently.18

Python

import pandas as pd  
import numpy as np  
import plotly.express as px

def process\_cme\_gold\_data(file\_path):  
    \# Load VOI file containing strike-level OI  
    df \= pd.read\_csv(file\_path)  
    \# Filter for active gold options and clean data  
    gold\_opts \= df\[(df\['Product Code'\] \== 'GC') & (df \== 'O')\]  
    gold\_opts \= pd.to\_numeric(gold\_opts)  
    gold\_opts\['OI'\] \= pd.to\_numeric(gold\_opts\['Open Interest'\])  
    return gold\_opts

def calculate\_max\_pain(gold\_opts):  
    strikes \= sorted(gold\_opts.unique())  
    pain\_map \=  
      
    for k in strikes:  
        \# Calculate loss for call writers (Gold Price \> Strike)  
        calls \= gold\_opts\[gold\_opts\['Put/Call'\] \== 'C'\]  
        call\_loss \= ((k \- calls).clip(lower=0) \* calls\['OI'\]).sum()  
          
        \# Calculate loss for put writers (Strike \> Gold Price)  
        puts \= gold\_opts\[gold\_opts\['Put/Call'\] \== 'P'\]  
        put\_loss \= ((puts \- k).clip(lower=0) \* puts\['OI'\]).sum()  
          
        pain\_map.append({'Strike': k, 'Total Pain': call\_loss \+ put\_loss})  
      
    return pd.DataFrame(pain\_map)

def generate\_oi\_heatmap(gold\_opts):  
    \# Pivot data to create Heatmap Matrix  
    heatmap\_matrix \= gold\_opts.pivot\_table(index='Strike', columns='Contract Month', values='OI', aggfunc='sum')  
    fig \= px.imshow(heatmap\_matrix,   
                    color\_continuous\_scale='Viridis',  
                    title='CME Gold Option Open Interest Heatmap (Strike vs Expiry)')  
    fig.show()

18

### **Strategy Integration: The Open Interest Breakout System**

A sophisticated gold strategy utilizes the 20-day rolling high (resistance) and low (support) as entry triggers, but only when confirmed by a specific "open interest profile".27 In this design, a bullish breakout is defined as the gold closing price exceeding the 20-day resistance, provided that the open interest has increased by more than 5% on the day of the move and the RSI indicates the market is not yet overbought (e.g., RSI \< 70).27

To refine this, traders incorporate the Average True Range (ATR) for volatility-adjusted position sizing.34 For instance, a "state machine" approach may be used where the system enters a "Scanning" phase upon a technical signal, but only moves to "Entry" once the heatmap confirms that the breakout strike has transitioned from a high-OI stabilization zone to a "short-gamma" acceleration zone.5

## **Advanced Predictive Modeling: ARIMA-Neural Network Hybrid**

Research in gold price prediction has increasingly moved toward hybrid models that combine time-series econometrics with artificial intelligence.36 In these frameworks, the ARIMA (Auto-Regressive Integrated Moving Average) component is used to model the linear trends in gold prices, while Stepwise Regression is utilized to select the most impactful exogenous features from the CME data—primarily daily changes in open interest, volume, and implied volatility.9

The selected features are then fed into an Artificial Neural Network (ANN), which identifies non-linear patterns and "psychological" behaviors in the market participants.36 The inclusion of open interest as a primary input feature significantly enhances the accuracy of these models. This is because OI represents the "energy" available for a price move; a technical pattern on a chart is far more likely to resolve in a sustained trend if the neural network detects a corresponding structural buildup in the open interest heatmap.1

## **Risk Management and Backtesting Integrity**

A critical challenge in developing an open interest strategy for gold is the "reporting lag" inherent in CME data.6 Official open interest for a given trading day is only finalized and published the following morning.6 Therefore, a backtest must be "lagged" by one day to avoid look-ahead bias.37 If a strategy uses Monday's open interest to make a decision, the trade cannot realistically be executed until Tuesday's open.37

### **Performance Metrics and Behavioral Reality**

The validation of these strategies requires a thorough analysis of risk-adjusted returns.35 For gold futures systems, the Sharpe Ratio and Maximum Drawdown are the primary metrics of interest.35 A Sharpe Ratio above 1.0 is generally considered excellent for gold, given its inherent volatility.35 However, traders must also consider the "Profit Factor" (the ratio of gross gains to gross losses) and the "Win Rate".35

| Backtesting Metric | Target for Gold Strategy | Quantitative Justification |
| :---- | :---- | :---- |
| Sharpe Ratio | \> 0.85 | High volatility necessitates strong risk-adjusted returns |
| Max Drawdown | \< 15% | Gold can experience deep corrections; protection is vital |
| Profit Factor | \> 1.6 | Essential for overcoming commissions and slippage |
| 1-Day Lag applied | Mandatory | Prevents look-ahead bias and ensures execution realism |

35

In practice, the success of an open interest strategy depends on the liquidity of the strikes being analyzed. Low-volume or far-out-of-the-money strikes often have wider bid-ask spreads, which can erode the alpha of a strategy through slippage.10 Therefore, quantitative filters are typically applied to only consider strikes with a minimum open interest (e.g., \> 500 contracts) and consistent daily volume.10

## **Conclusions and Strategic Outlook**

The use of CME COMEX gold open interest and heatmap data represents a significant advancement over traditional technical analysis by incorporating the structural and mechanical realities of the derivatives market.5 By identifying zones of institutional commitment and dealer gamma exposure, quantitative traders can move beyond predicting "where" the price might go and begin understanding "why" and "how" the market is being forced toward specific levels.5

The integration of Max Pain theory, COT disaggregation, and Pythonic machine-learning frameworks allows for the construction of a multi-layered gold strategy that is both statistically robust and aligned with institutional market microstructure.8 As the gold market continues to evolve with the increasing influence of algorithmic market making and global macroeconomic shifts, the ability to decode the "risk atlas" provided by open interest heatmaps will remain an indispensable tool for the modern professional trader.2 Ultimately, the success of such a system relies on the rigorous application of backtesting standards, particularly the mitigation of reporting lags and the prioritization of liquidity-rich strikes to ensure that the theoretical alpha translates into realized profit in the competitive arena of precious metals futures.10

#### **Works cited**

1. Open Interest \- CME Group, accessed February 19, 2026, [https://www.cmegroup.com/education/lessons/open-interest](https://www.cmegroup.com/education/lessons/open-interest)  
2. Gold Open Interest Chart | World Gold Council, accessed February 19, 2026, [https://www.gold.org/goldhub/data/gold-open-interest](https://www.gold.org/goldhub/data/gold-open-interest)  
3. Building a Strategy with Open Interest \- Build Alpha, accessed February 19, 2026, [https://www.buildalpha.com/free-friday-18-building-a-strategy-with-open-interest/](https://www.buildalpha.com/free-friday-18-building-a-strategy-with-open-interest/)  
4. Identifying Options with High Open Interest and Volume \- TradersPost Blog, accessed February 19, 2026, [https://blog.traderspost.io/article/identifying-options-with-high-open-interest-and-volume](https://blog.traderspost.io/article/identifying-options-with-high-open-interest-and-volume)  
5. The value of the Option Open Interest Heatmap in futures trading for ..., accessed February 19, 2026, [https://www.tradingview.com/chart/6EH2026/ooDnZDcs-The-value-of-the-Option-Open-Interest-Heatmap-in-futures-trading/](https://www.tradingview.com/chart/6EH2026/ooDnZDcs-The-value-of-the-Option-Open-Interest-Heatmap-in-futures-trading/)  
6. Open Interest | Trading Lesson | Traders' Academy \- Interactive Brokers, accessed February 19, 2026, [https://www.interactivebrokers.com/campus/trading-lessons/open-interest/](https://www.interactivebrokers.com/campus/trading-lessons/open-interest/)  
7. Futures Trading Basics: Open Interest vs Volume \- MetroTrade, accessed February 19, 2026, [https://www.metrotrade.com/open-interest-vs-volume/](https://www.metrotrade.com/open-interest-vs-volume/)  
8. Max Pain Options: Overview, Calculation, Example, Trading Strategy ..., accessed February 19, 2026, [https://www.strike.money/options/max-pain-options](https://www.strike.money/options/max-pain-options)  
9. On the Dynamics of Solid, Liquid and Digital Gold Futures, accessed February 19, 2026, [https://arxiv.org/pdf/2202.09845](https://arxiv.org/pdf/2202.09845)  
10. How to Interpret Open Interest and Price Data: A Trader's Guide \- Tradejini, accessed February 19, 2026, [https://www.tradejini.com/blogs/how-to-interpret-open-interest-and-price-data-a-traders-guide](https://www.tradejini.com/blogs/how-to-interpret-open-interest-and-price-data-a-traders-guide)  
11. Corn Open Interest Heatmap \- CME Group, accessed February 19, 2026, [https://www.cmegroup.com/tools-information/quikstrike/open-interest-heatmap-corn.html](https://www.cmegroup.com/tools-information/quikstrike/open-interest-heatmap-corn.html)  
12. Open Interest Heat Map Report \- CME Group, accessed February 19, 2026, [https://www.cmegroup.com/tools-information/quikstrike/quikstrike-user-guide-open-interest-heatmap.html](https://www.cmegroup.com/tools-information/quikstrike/quikstrike-user-guide-open-interest-heatmap.html)  
13. Python: Creating Heatmaps for Data Visualization \- KnowledgeCity, accessed February 19, 2026, [https://www-new.knowledgecity.com/en/library/L373344859/python-creating-heatmaps-for-data-visualization/](https://www-new.knowledgecity.com/en/library/L373344859/python-creating-heatmaps-for-data-visualization/)  
14. Open Interest Profile User Guide \- CME Group, accessed February 19, 2026, [https://www.cmegroup.com/tools-information/quikstrike/quikstrike-user-guides-open-interest.html](https://www.cmegroup.com/tools-information/quikstrike/quikstrike-user-guides-open-interest.html)  
15. GLD Open Interest Trends SPDR Gold Shares \- Market Chameleon, accessed February 19, 2026, [https://marketchameleon.com/Overview/GLD/OpenInterestTrends/](https://marketchameleon.com/Overview/GLD/OpenInterestTrends/)  
16. GLD Max Pain and Volatility Skew Charts for Gold SPDR ETF \- Barchart.com, accessed February 19, 2026, [https://www.barchart.com/etfs-funds/quotes/GLD/max-pain-chart](https://www.barchart.com/etfs-funds/quotes/GLD/max-pain-chart)  
17. What is Max Pain? Meaning, How to Calculate & Example | BlinkX, accessed February 19, 2026, [https://blinkx.in/en/knowledge-base/derivatives/what-is-max-pain](https://blinkx.in/en/knowledge-base/derivatives/what-is-max-pain)  
18. Updated-Max-Pain-Calculator \- GitHub, accessed February 19, 2026, [https://github.com/asad70/Options-Max-Pain-Calculator/blob/master/Updated-Max-Pain-Calculator](https://github.com/asad70/Options-Max-Pain-Calculator/blob/master/Updated-Max-Pain-Calculator)  
19. asad70/Options-Max-Pain-Calculator \- GitHub, accessed February 19, 2026, [https://github.com/asad70/Options-Max-Pain-Calculator](https://github.com/asad70/Options-Max-Pain-Calculator)  
20. Commitment of Traders \- CME Group, accessed February 19, 2026, [https://www.cmegroup.com/tools-information/quikstrike/commitment-of-traders.html](https://www.cmegroup.com/tools-information/quikstrike/commitment-of-traders.html)  
21. Long-term Trading Strategy with the COT Report \- FxScouts, accessed February 19, 2026, [https://fxscouts.com/forex-education/long-term-trading-strategy-with-the-cot-report/](https://fxscouts.com/forex-education/long-term-trading-strategy-with-the-cot-report/)  
22. Gold COT Data: Latest Index \- InsiderWeek, accessed February 19, 2026, [https://insider-week.com/en/cot/gold/](https://insider-week.com/en/cot/gold/)  
23. Commitments of Traders (COT) Charts \- Barchart.com, accessed February 19, 2026, [https://www.barchart.com/futures/commitment-of-traders](https://www.barchart.com/futures/commitment-of-traders)  
24. COT on forex and commodities \- Week to 10 Feb 2026 | Saxo, accessed February 19, 2026, [https://www.home.saxo/content/articles/commodities/cot-on-forex-and-commodities---week-to-10-feb-2026-16022026](https://www.home.saxo/content/articles/commodities/cot-on-forex-and-commodities---week-to-10-feb-2026-16022026)  
25. CME DataMine API, accessed February 19, 2026, [https://www.cmegroup.com/market-data/datamine-api.html](https://www.cmegroup.com/market-data/datamine-api.html)  
26. CME Historical Data: Complete Guide to Futures Prices & API Access \- QuantVPS, accessed February 19, 2026, [https://www.quantvps.com/blog/cme-historical-data-complete-guide](https://www.quantvps.com/blog/cme-historical-data-complete-guide)  
27. Breakout Trading Strategy in Different Market Conditions \- EODHD, accessed February 19, 2026, [https://eodhd.com/financial-academy/fundamental-analysis-examples/breakout-trading-strategy-in-different-market-conditions](https://eodhd.com/financial-academy/fundamental-analysis-examples/breakout-trading-strategy-in-different-market-conditions)  
28. Heatmaps in Python \- Plotly, accessed February 19, 2026, [https://plotly.com/python/heatmaps/](https://plotly.com/python/heatmaps/)  
29. DataMine List API \- CME Group, accessed February 19, 2026, [https://www.cmegroup.com/datamine/datamine-list-api.html](https://www.cmegroup.com/datamine/datamine-list-api.html)  
30. Volume and Open Interest \- CME Group Client Systems Wiki \- Confluence, accessed February 19, 2026, [https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457092154](https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457092154)  
31. Visualizing Options Market Data in Python: Implied Volatility, Open Interest, and Max Pain, accessed February 19, 2026, [https://dev.to/dm8ry/visualizing-options-market-data-in-python-implied-volatility-open-interest-and-max-pain-4emd](https://dev.to/dm8ry/visualizing-options-market-data-in-python-implied-volatility-open-interest-and-max-pain-4emd)  
32. Seaborn Heatmaps: A Guide to Data Visualization \- DataCamp, accessed February 19, 2026, [https://www.datacamp.com/tutorial/seaborn-heatmaps](https://www.datacamp.com/tutorial/seaborn-heatmaps)  
33. Break the Market: Building a Python Breakout Strategy with Live Gold Data, accessed February 19, 2026, [https://medium.datadriveninvestor.com/break-the-market-building-a-python-breakout-strategy-with-live-gold-data-bd6e9ea9cb4f](https://medium.datadriveninvestor.com/break-the-market-building-a-python-breakout-strategy-with-live-gold-data-bd6e9ea9cb4f)  
34. Top 3 Gold Futures Trading Strategies for Volatile Markets \- NinjaTrader, accessed February 19, 2026, [https://ninjatrader.com/futures/blogs/gold-futures-trading-strategies-for-volatile-markets/](https://ninjatrader.com/futures/blogs/gold-futures-trading-strategies-for-volatile-markets/)  
35. ilahuerta-IA/backtrader-pullback-window-xauusd: Professional algorithmic trading strategy for Gold (XAU/USD) with 4-phase state machine entry system. Sharpe 0.89 | PF 1.64 | WR 55.43% | DD 5.81% | \+44.75% return over 5 years. \- GitHub, accessed February 19, 2026, [https://github.com/ilahuerta-IA/backtrader-pullback-window-xauusd](https://github.com/ilahuerta-IA/backtrader-pullback-window-xauusd)  
36. \[2505.01402\] Predicting the Price of Gold in the Financial Markets Using Hybrid Models, accessed February 19, 2026, [https://arxiv.org/abs/2505.01402](https://arxiv.org/abs/2505.01402)  
37. Do we need to lag values for backtesting? \- Quantitative Finance Stack Exchange, accessed February 19, 2026, [https://quant.stackexchange.com/questions/29962/do-we-need-to-lag-values-for-backtesting](https://quant.stackexchange.com/questions/29962/do-we-need-to-lag-values-for-backtesting)  
38. Reporting lags for Backtesting : r/CFA \- Reddit, accessed February 19, 2026, [https://www.reddit.com/r/CFA/comments/11y42ad/reporting\_lags\_for\_backtesting/](https://www.reddit.com/r/CFA/comments/11y42ad/reporting_lags_for_backtesting/)  
39. Backtesting Systematic Trading Strategies in Python: Considerations and Open Source Frameworks | QuantStart, accessed February 19, 2026, [https://www.quantstart.com/articles/backtesting-systematic-trading-strategies-in-python-considerations-and-open-source-frameworks/](https://www.quantstart.com/articles/backtesting-systematic-trading-strategies-in-python-considerations-and-open-source-frameworks/)  
40. Backtest a Profitable Trend-Following Strategy using Python \- Concretum Group, accessed February 19, 2026, [https://concretumgroup.com/backtest-a-profitable-trend-following-strategy-using-python/](https://concretumgroup.com/backtest-a-profitable-trend-following-strategy-using-python/)  
41. What Is Backtesting & How to Backtest a Trading Strategy Using Python \- QuantInsti, accessed February 19, 2026, [https://www.quantinsti.com/articles/backtesting-trading/](https://www.quantinsti.com/articles/backtesting-trading/)  
42. Is this bid-ask spread for gold GC futures options normal? : r/FuturesTrading \- Reddit, accessed February 19, 2026, [https://www.reddit.com/r/FuturesTrading/comments/1qr25kb/is\_this\_bidask\_spread\_for\_gold\_gc\_futures\_options/](https://www.reddit.com/r/FuturesTrading/comments/1qr25kb/is_this_bidask_spread_for_gold_gc_futures_options/)  
43. Filter Trade Ideas: Open Interest & Trader Count \- Option Alpha, accessed February 19, 2026, [https://optionalpha.com/blog/expanded-trade-ideas-filters-include-open-interest-and-trader-count](https://optionalpha.com/blog/expanded-trade-ideas-filters-include-open-interest-and-trader-count)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAYCAYAAACFms+HAAACd0lEQVR4Xu2WXWiOYRzGL5nFzJAJzVopLaV8F6IIRYsWJ0rjgFo5kFbLx5HsBPncTiRlO1BIJJSQkRPZ0Ypai7IdTFnjxIkUuy7/+/be7+3J9r7v9Ky8V/3quT+e5/l/Pf/7AYoq6v/SRvKR/Az4TD6566/kIqnwN4w3XSXfybpofjnMicekPFpLXdPIS/KezInWZOxz8oNszl5KX4vIELlNSqK1maQLydlIXTtg9dwUL1BryDfyikyP1lJXK5IjKkOfkkGyMlpLXb6GFdXr5IqjgwyQa2S+3zye5Ov7Cakh8wImB/vy0URSFs1prHlpCemFNQY1iJzk6/t4vDAG2g3LmJdK7xFZEcw1wko1Z+mmf9XqdDbIMC9FWNGtdGN1MHWyPb93jFK+f38gVdlLiZpLzpEHZFMwX0vOuPktZCks0jqR75MDpBl2iPWTS6Qa5kAnrFy9psAyJYf0rsROtph8IQ8xcj3rgfpoF5AN5BYpJTvJPdgLFIgWMhVmjIzy0ZWU3TAD6mIvYGeFpGfcJbvcuJ5sc9e/tJ704c//k/3hpkgy4A0sQ/tgL9PcW3Ielu7LZKvbr7G61AQ31v5nZJUbS3F9a/yONJAj+EvEc5V6eTvsx0tO6iPrIQuDPV5xdOMMJNW3WvBpZJwtWLNIN9nuxsdgdShjXsNap6QX6qdsNjLRXUbqkMnAJHIQVnJyZC0ymZazirSXvim16Lyl+j5L9pLD5AKsjmXoIXIKZlgbLAvaf5OcgP1GyFh9tDor1HbljErgDjlJVsMkI2/AniUHjsKeVbBmIPkj1umrtVA6ZOJDRc7KCS9day6U7lM5hfuKKioXDQPrYnIeERY7wAAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAYCAYAAAD+vg1LAAABWUlEQVR4Xu3UPyiFURjH8UcoMkjEYDGglKQsFAMZrDbCqqSskuXKYFcmdotFkYHR4DJYlEmxGAiTSf58n55zes8997rd97pZ+NWn23uep/ue+9z3vCL/+e2M4hGfgWfMBT3rUX0fDUG9aHbwgfG4QLqQxSzqolrRNOECt2jPLckYDtARrZeUHjzhUJIdVWMJG6h3a6kzIza7ZXet89sSm3OVbyonm3jDMLpxiTM0hk1p4+d7h0Xsin2p/pETQV/q+Pm+YxW1mBIbjd6kJmnNS59Yb8Fx+fmuSNLQhmu8oNetFcoC5uNFH31+/XzDZMRuqJ+p4+d7I7bLMLpT3bHuPK7pU7OGbfnmDx7AK/Ykf5Z6reu6az1xYSbRjyMMhQU9tveSe/4fMO3qrTiP6lfodHU94oM4FvvVFU3GqWhacCq2a332yz7ycZpxIvY6HYlqP44epJLfyX8sX2RcRWvwi0ptAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABdUlEQVR4Xu2VvStGURzHf0J5K1lIDPKasshq8ZIMmAl/gTISFiXZlc1uYRAGNlm8DBZlUiwGwmSSl8+vc497nh9PPe5zk8GnPj3d8z0955zfOfdckX/+Gj14j++BjzgZ9Fky+TaWB3lOrOMb9tsAWvAEJ7DEZDlRhWd4jXWZkfTiLjaY9h/Rjg+4J/EMC3EaV7A0akvMuLjazkbPWt81cftQ4Dvlwyq+YDe24jkeY2XYKSm+/jc4hRvi/lw3fDDolxhf/1dcwGIcFVcyHawo7votuj86sVobeHz95ySudw1e4hN2RG3ZqBd3xLMOoKGvf8iiuIH1NzG+/lfiZh2iM9cV6Epspuhqh3ELB0z2SRc+46Z8rbU+a7uuQt9gix6APnGD7GNZGOp1cCuZ98sdjkV5NZ6a/AKbo1xpE3cg5nE5aE8Vfet3cMQGaaH31hE22iAttNQHWGGDtNC7K/X66+bq0R3CQ+zMjPNHb9oZcV+5JpP9Dh/6kEj5CfiFYgAAAABJRU5ErkJggg==>