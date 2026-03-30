import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.tools.web_search import WebSearchTool
from app.tools.market_reader import MarketReaderTool


@pytest.mark.asyncio
async def test_web_search_timeout_handling():
    """Verify that a slow search provider triggers the configured timeout."""

    from dogpile.cache.api import NO_VALUE

    mock_region = MagicMock()
    mock_region.get.return_value = NO_VALUE

    with patch(
        "app.tools.web_search.config", MagicMock(ki_tool_timeout=1)
    ):  # Set timeout to 1s
        with patch("asyncio.to_thread", side_effect=asyncio.TimeoutError):
            with patch(
                "app.tools.web_search.get_cache_region", return_value=mock_region
            ):
                results = await WebSearchTool.search("Slow news")

                # Should return empty list on timeout, not crash
                assert results == []


@pytest.mark.asyncio
async def test_market_reader_timeout_handling():
    """Verify that MarketReader respects the institutional timeout."""

    from dogpile.cache.api import NO_VALUE

    mock_region = MagicMock()
    mock_region.get.return_value = NO_VALUE

    with patch("httpx.AsyncClient.get", side_effect=asyncio.TimeoutError):
        with patch("app.tools.market_reader.config", MagicMock(ki_tool_timeout=1)):
            with patch(
                "app.tools.market_reader.get_cache_region", return_value=mock_region
            ):
                price = await MarketReaderTool.get_spot_price("Gold")

                # Should return None on timeout
                assert price is None


@pytest.mark.asyncio
async def test_market_reader_http_error():
    """Verify that MarketReader handles 500/404 errors gracefully."""

    from dogpile.cache.api import NO_VALUE

    mock_region = MagicMock()
    mock_region.get.return_value = NO_VALUE

    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        with patch(
            "app.tools.market_reader.get_cache_region", return_value=mock_region
        ):
            price = await MarketReaderTool.get_spot_price("BTC")
            assert price is None
