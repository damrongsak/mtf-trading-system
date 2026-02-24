# Data Pipeline Service

The **MTF Olympus Data Pipeline** is responsible for ingesting market data (Candlestick and Real-time Ticks), economic calendars, news, and COT reports.

## 🚀 Primary Data Source: cTrader
This service is optimized for **cTrader** as the primary institutional data provider. 

### Key Features
*   **Real-time Streaming**: High-performance tick data ingestion via cTrader's Open API.
*   **Dual-layer Price Cache**: Atomic Redis caching (L2) and in-memory local caching (L1) for microsecond price retrieval.
*   **Historical Backfill**: Robust job scheduler for syncing historical candles.
*   **Event-Driven Architecture**: Broadcasts market events (Ticks, Candle Completion, Trade Sync) via Redis Streams and Pub/Sub.

## 🏗️ Architecture
- **Adapters**: Pluggable adapters for cTrader (Primary) and OANDA (Secondary).
- **Stream Manager**: Manages concurrent streaming connections and high-performance EFP calculations.
- **Job Scheduler**: APScheduler-based jobs for background data synchronization.

## 🛠️ Performance Optimization
The pipeline uses **Redis Pipelines** and **MessagePack** (Optional/EFP Path) to ensure minimal latency during market volatility. Price updates are stored in Redis Hashes (`market_data:spot:{symbol}`) for O(1) read access by Trading Strategies.
