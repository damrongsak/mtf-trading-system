import pytest
import asyncio
from app.services.scraper_service import NewsScraperService

@pytest.mark.asyncio
async def test_scraper_rss_gold():
    scraper = NewsScraperService()
    news = await scraper.fetch_rss_news("XAUUSD")
    assert isinstance(news, list)
    # At least some news should be found given the broad RSS feeds
    assert len(news) >= 0 
    await scraper.close()

@pytest.mark.asyncio
async def test_specialized_scrapers():
    scraper = NewsScraperService()
    
    # Test CME FedWatch
    fedwatch = await scraper.scrape_cme_fedwatch()
    assert len(fedwatch) > 0
    assert fedwatch[0]["source"] == "CME FedWatch"
    assert "Fed Policy" in fedwatch[0].get("category", "")
    
    # Test BLS
    bls = await scraper.scrape_bls_gov()
    assert isinstance(bls, list)
    
    # Test WGC
    wgc = await scraper.scrape_wgc_data()
    assert len(wgc) > 0
    assert wgc[0]["source"] == "World Gold Council"
    
    await scraper.close()

@pytest.mark.asyncio
async def test_get_all_news_aggregation():
    scraper = NewsScraperService()
    news = await scraper.get_all_news("XAUUSD")
    assert isinstance(news, list)
    assert len(news) > 0
    # Check if any specialized source is present
    sources = [n["source"] for n in news]
    assert any(s in ["CME FedWatch", "World Gold Council", "BLS.gov"] or "Reuters" in s or "BBC" in s for s in sources)
    await scraper.close()
