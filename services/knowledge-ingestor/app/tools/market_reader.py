import httpx
import asyncio
from typing import Optional
from dogpile.cache import make_region
from app.core.app_config import config
from app.core.logging_config import get_logger

logger = get_logger("MarketReader")

_cache_region = None


def get_cache_region():
    global _cache_region
    if _cache_region is None:
        _cache_region = make_region().configure(
            "dogpile.cache.redis",
            arguments={
                "url": f"redis://{config.falkor_host}:{config.falkor_port}/1",
                "redis_expiration_time": 3600 * 2,  # 2 hours TTL for prices
                "distributed_lock": True,
                "thread_local_lock": False,
            },
        )
    return _cache_region


class MarketReaderTool:
    """
    Tool for fetching real-time market data to verify document-based inferences.
    Initial implementation uses free/public APIs (e.g., Yahoo Finance via unofficial endpoints or Alpha Vantage).
    """

    @staticmethod
    async def get_spot_price(symbol: str) -> Optional[float]:
        """Fetch spot price for a given symbol (e.g., XAU, BTC, AAPL)"""
        from dogpile.cache.api import NO_VALUE

        # Mapping common symbols to Yahoo Finance tickers
        mappings = {
            "Gold": "GC=F",
            "XAU": "GC=F",
            "XAUUSD": "GC=F",
            "Bitcoin": "BTC-USD",
            "BTC": "BTC-USD",
            "Silver": "SI=F",
            "XAG": "SI=F",
            "Crude Oil": "CL=F",
            "S&P 500": "^GSPC",
        }

        ticker = mappings.get(symbol, symbol)

        cache_key = f"market_spot_price:{ticker}"
        region = get_cache_region()
        cached_price = region.get(cache_key)

        if cached_price is not NO_VALUE:
            logger.info(f"⚡ Cached price hit for: {ticker} = {cached_price}")
            return float(cached_price)

        logger.info(f"🔍 Searching real-time price for: {ticker}")

        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            timeout = getattr(config, "ki_tool_timeout", 15)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    price = float(
                        data["chart"]["result"][0]["meta"]["regularMarketPrice"]
                    )

                    # Store in cache
                    region.set(cache_key, price)
                    return price
                else:
                    logger.warning(
                        f"Failed to fetch price for {ticker}: HTTP {response.status_code}"
                    )
                    return None

        except asyncio.TimeoutError:
            logger.error(f"⏱️ MarketReader timed out for: {ticker}")
            return None
        except Exception as e:
            logger.error(f"❌ MarketReader failed for {ticker}: {e}")
            return None


if __name__ == "__main__":
    import asyncio

    async def test():
        price = await MarketReaderTool.get_spot_price("Gold")
        print(f"Current Gold Price: ${price}")

    asyncio.run(test())
