import logging
import json
import aiohttp
import feedparser
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from app.services.base import BaseService
from app.core.config import settings
import yfinance as yf

logger = logging.getLogger(__name__)

class NewsScraperService(BaseService):
    """
    Service to scrape real-time news from RSS feeds and financial websites.
    Provides a free and open-source alternative to NewsAPI.
    """
    
    def __init__(self):
        super().__init__()
        # RSS Feeds (Free and Reliable)
        self.rss_feeds = {
            "Reuters (Business)": "https://news.google.com/rss/search?q=when:7d+Reuters+Business&hl=en-US&gl=US&ceid=US:en",
            "CNBC (Economy)": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
            "Investing (Gold)": "https://www.investing.com/rss/news_95.rss",
            "Bloomberg (Geopolitics)": "https://news.google.com/rss/search?q=when:7d+Bloomberg+Iran+Israel+War&hl=en-US&gl=US&ceid=US:en",
            "Gold Market (Macro)": "https://news.google.com/rss/search?q=when:7d+Gold+Price+Trump+Fed&hl=en-US&gl=US&ceid=US:en"
        }
        
    async def fetch_rss_news(self, symbol: str = "XAUUSD") -> List[Dict[str, Any]]:
        """Parses RSS feeds for relevant news with enhanced Geopolitical filtering."""
        all_articles = []
        
        # Base Keywords for XAUUSD
        base_keywords = ["gold", "xau", "fed", "inflation", "dollar", "treasury", "yield"]
        
        # Geopolitical / Macro Keywords (High Impact on Gold)
        geopol_keywords = [
            "middle east", "israel", "iran", "gaza", "lebanon", "red sea", "war", "conflict", 
            "geopolit", "sanction", "trade war", "tariffs", "chip", "semiconductor", "nvidia", 
            "ai regulation", "taiwan", "china economy", "brics", "nato", "russia", "ukraine",
            "evacuation", "embassy", "consulate", "repatriation", "leave immediately", "advisory"
        ]
        
        keywords = (base_keywords + geopol_keywords) if symbol == "XAUUSD" else [symbol]
        
        # Dynamic Keywords from AI Analyst (Feedback Loop)
        dynamic_keywords = []
        try:
            redis_client = await self.get_redis()
            drivers_key = f"news:dynamic_keywords:{symbol}"
            cached_drivers = await redis_client.get(drivers_key)
            if cached_drivers:
                dynamic_keywords = json.loads(cached_drivers)
                logger.info(f"🧠 Applying Dynamic Re-ranking for {symbol}: {dynamic_keywords}")
        except Exception as e:
            logger.warning(f"Could not fetch dynamic keywords: {e}")
        
        for name, url in self.rss_feeds.items():
            try:
                # We use aiohttp to fetch and then feedparser to parse
                session = await self.get_session()
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        continue
                    xml_content = await response.text()
                    
                feed = feedparser.parse(xml_content)
                
                for entry in feed.entries:
                    title = entry.get("title", "")
                    
                    # Filter by keywords and calculate simple relevance score
                    match_count = sum(1 for kw in keywords if kw.lower() in title.lower())
                    
                    if match_count > 0:
                        # Geopolitical weight: news with geopol terms gets prioritized
                        has_geopol = any(gw.lower() in title.lower() for gw in geopol_keywords)
                        
                        # Critical terms: even higher priority
                        critical_terms = ["war", "evacuation", "leave immediately", "strike", "attack", "conflict", "bomb", "missile"]
                        is_critical = any(ct.lower() in title.lower() for ct in critical_terms)
                        
                        # Standardize to NewsAPI format
                        pub_at = entry.get("published", datetime.utcnow().isoformat())
                        try:
                            # Try parsing to ISO if possible
                            if getattr(entry, "published_parsed", None):
                                pub_at = datetime(*entry.published_parsed[:6]).isoformat()
                        except:
                            pass
                            
                        # Dynamic Re-ranking bonus (+3)
                        has_dynamic = any(dk.lower() in title.lower() for dk in dynamic_keywords)
                        
                        item = {
                            "title": title,
                            "source": name,
                            "url": entry.get("link", ""),
                            "publishedAt": pub_at,
                            "relevance": match_count + (5 if is_critical else (2 if has_geopol else 0)) + (3 if has_dynamic else 0)
                        }
                        all_articles.append(item)
            except Exception as e:
                logger.error(f"Failed to fetch RSS from {name}: {e}")
                
        return sorted(all_articles, key=lambda x: x["publishedAt"], reverse=True)[:15]

    async def scrape_investing_gold(self) -> List[Dict[str, Any]]:
        """Directly scrapes Investing.com Gold News for real-time updates."""
        url = "https://www.investing.com/news/gold-news"
        articles = []
        
        try:
            session = await self.get_session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    return []
                html = await response.text()
                
            # Direct scraping is often blocked by Cloudflare/Anti-bot
            # We try some common selectors but rely on RSS as primary
            news_items = (
                soup.select('article div.text-container') or 
                soup.select('.newsItem') or 
                soup.select('div.newstext') or
                soup.select('li.news-item')
            )
            
            for item in news_items:
                link_tag = item.select_one('a.title') or item.select_one('a')
                if not link_tag: continue
                
                title = link_tag.get_text(strip=True)
                if not title: continue
                
                href = link_tag.get('href', '')
                if not href or href == '#': continue
                
                full_url = f"https://www.investing.com{href}" if href.startswith('/') else href
                
                time_tag = item.select_one('span.date') or item.select_one('time')
                pub_at = time_tag.get('datetime') if time_tag and time_tag.get('datetime') else datetime.utcnow().isoformat()
                
                articles.append({
                    "title": title,
                    "source": "Investing.com (Scraped)",
                    "url": full_url,
                    "publishedAt": pub_at
                })
        except Exception as e:
            logger.error(f"Investing.com scrape failed: {e}")
            
        return articles[:10]

    async def fetch_yfinance_news(self, symbol: str = "GC=F") -> List[Dict[str, Any]]:
        """Fetches news via yfinance library."""
        try:
            # Gold futures often have better news on yfinance
            yf_symbol = "GC=F" if symbol == "XAUUSD" else symbol
            ticker = yf.Ticker(yf_symbol)
            news = ticker.news
            
            articles = []
            for n in news:
                pub_at = datetime.fromtimestamp(n.get("providerPublishTime", 0)).isoformat()
                articles.append({
                    "title": n.get("title"),
                    "source": n.get("publisher"),
                    "url": n.get("link"),
                    "publishedAt": pub_at
                })
            return articles
        except Exception as e:
            logger.error(f"yfinance news fetch failed for {symbol}: {e}")
            return []

    async def get_all_news(self, symbol: str = "XAUUSD") -> List[Dict[str, Any]]:
        """Aggregates all news sources and deduplicates."""
        # Parallel fetch
        tasks = [
            self.fetch_rss_news(symbol),
            self.scrape_investing_gold() if symbol == "XAUUSD" else asyncio.sleep(0, result=[]),
            self.fetch_yfinance_news(symbol)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Flatten and deduplicate by URL or Title
        all_raw = [item for sublist in results for item in sublist if item]
        
        seen_titles = set()
        deduped = []
        for article in all_raw:
            title = article.get("title")
            if not title:
                continue
            title_clean = title.lower().strip()
            if title_clean not in seen_titles:
                seen_titles.add(title_clean)
                deduped.append(article)
                
        # Sort by relevance first, then by date
        # This ensures Geopolitical news (weighted +2) stays at the top if recent
        return sorted(deduped, key=lambda x: (x.get("relevance", 0), x["publishedAt"]), reverse=True)[:20]
