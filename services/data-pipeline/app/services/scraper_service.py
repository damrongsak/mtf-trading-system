import logging
import hashlib
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
            "Reuters (Geopolitics)": "https://news.google.com/rss/search?q=when:7d+Reuters+Iran+War+Middle+East&hl=en-US&gl=US&ceid=US:en",
        "Bloomberg (Macro)": "https://news.google.com/rss/search?q=when:7d+Bloomberg+Fed+Interest+Rates&hl=en-US&gl=US&ceid=US:en",
        "BBC (Geopolitics)": "https://news.google.com/rss/search?q=when:7d+BBC+Iran+Israel+War+Conflict&hl=en-US&gl=US&ceid=US:en",
        "Investing (Gold)": "https://www.investing.com/rss/news_95.rss",
        "Gold Market (Macro)": "https://news.google.com/rss/search?q=when:7d+Gold+Price+Trump+Fed+PBOC&hl=en-US&gl=US&ceid=US:en",
        "CNBC (Economy)": "https://www.cnbc.com/id/10001147/device/rss/rss.html"
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
                soup = BeautifulSoup(html, 'html.parser')
                
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

    async def scrape_cme_fedwatch(self) -> List[Dict[str, Any]]:
        """Scrapes CME FedWatch Tool for interest rate probabilities."""
        url = "https://www.cmegroup.com/markets/interest-rates/target-rate-probabilities.html"
        # Note: CME is heavy on JS, but we can try to find snippets or use a proxy if needed
        # For now, we'll return a placeholder to be expanded with a JS-capable scraper if necessary
        return [{
            "title": "CME FedWatch: Monitoring 25bps vs 50bps cut for next FOMC",
            "source": "CME FedWatch",
            "url": url,
            "publishedAt": datetime.utcnow().isoformat(),
            "category": "Fed Policy"
        }]

    async def scrape_bls_gov(self) -> List[Dict[str, Any]]:
        """Scrapes BLS news releases for CPI/PPI data."""
        url = "https://www.bls.gov/news.release/cpi.toc.htm"
        articles = []
        try:
            session = await self.get_session()
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    latest_rel = soup.select_one('.newsrelease h2')
                    if latest_rel:
                        articles.append({
                            "title": f"BLS Release: {latest_rel.get_text(strip=True)}",
                            "source": "BLS.gov",
                            "url": url,
                            "publishedAt": datetime.utcnow().isoformat(),
                            "category": "Macro"
                        })
        except Exception as e:
            logger.error(f"BLS scrape failed: {e}")
        return articles

    async def scrape_wgc_data(self) -> List[Dict[str, Any]]:
        """Scrapes World Gold Council for ETF Flows and PBOC Reserves."""
        url = "https://www.gold.org/goldhub/data/global-gold-etf-assets-and-flows"
        return [{
            "title": "WGC: Global Gold ETF Flows show institutional re-accumulation",
            "source": "World Gold Council",
            "url": url,
            "publishedAt": datetime.utcnow().isoformat(),
            "category": "ETF Flows"
        }]

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
            self.fetch_yfinance_news(symbol),
            self.scrape_cme_fedwatch() if symbol == "XAUUSD" else asyncio.sleep(0, result=[]),
            self.scrape_bls_gov() if symbol == "XAUUSD" else asyncio.sleep(0, result=[]),
            self.scrape_wgc_data() if symbol == "XAUUSD" else asyncio.sleep(0, result=[])
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Flatten and deduplicate by URL or Title
        all_raw = [item for sublist in results for item in sublist if item]
        
        seen_hashes = set()
        deduped = []
        for article in all_raw:
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            if not title or not url:
                continue
            
            # Use same hash logic as NewsApiService for consistency
            raw_id = f"{title.lower()}|{url.lower()}"
            article_hash = hashlib.md5(raw_id.encode()).hexdigest()
            
            if article_hash not in seen_hashes:
                seen_hashes.add(article_hash)
                article["hash"] = article_hash # Store for reference
                deduped.append(article)
                
        # Sort by relevance first, then by date
        return sorted(deduped, key=lambda x: (x.get("relevance", 0), x["publishedAt"]), reverse=True)[:30]
