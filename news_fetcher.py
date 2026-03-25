import httpx
import feedparser
import json
import logging
import os
from bs4 import BeautifulSoup
from config import (
    NEWS_API_KEY,
    NEWS_API_BASE_URL,
    CRYPTOPANIC_API_KEY,
    CRYPTOPANIC_BASE_URL,
    RSS_FEEDS,
)

logger = logging.getLogger(__name__)

_PUBLISHED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "published_urls.json")
_MAX_STORED = 2000

_published_urls: set[str] = set()


def _load_published() -> None:
    global _published_urls
    if os.path.exists(_PUBLISHED_FILE):
        try:
            with open(_PUBLISHED_FILE, "r", encoding="utf-8") as f:
                _published_urls = set(json.load(f))
            logger.info(f"Loaded {len(_published_urls)} published URLs from disk.")
        except Exception as e:
            logger.warning(f"Could not load published URLs: {e}")
            _published_urls = set()


def _save_published() -> None:
    try:
        data = list(_published_urls)
        if len(data) > _MAX_STORED:
            data = data[-_MAX_STORED:]
            _published_urls.clear()
            _published_urls.update(data)
        with open(_PUBLISHED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"Could not save published URLs: {e}")


def _mark_published(url: str) -> None:
    _published_urls.add(url)
    _save_published()


def _is_published(url: str) -> bool:
    return url in _published_urls


_load_published()


async def fetch_newsapi_articles(query: str = "cryptocurrency bitcoin ethereum", count: int = 5) -> list[dict]:
    if not NEWS_API_KEY:
        return []
    url = f"{NEWS_API_BASE_URL}/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": count * 2,
        "apiKey": NEWS_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            articles = response.json().get("articles", [])
            result = []
            for a in articles:
                link = a.get("url", "")
                if _is_published(link):
                    continue
                result.append({
                    "title": a.get("title", ""),
                    "summary": a.get("description", "") or "",
                    "url": link,
                    "source": a.get("source", {}).get("name", "NewsAPI"),
                    "image_url": a.get("urlToImage", ""),
                })
                if len(result) >= count:
                    break
            return result
    except Exception as e:
        logger.error(f"NewsAPI error: {e}")
        return []


async def fetch_cryptopanic_news(count: int = 5) -> list[dict]:
    if not CRYPTOPANIC_API_KEY:
        return []
    url = f"{CRYPTOPANIC_BASE_URL}/posts/"
    params = {
        "auth_token": CRYPTOPANIC_API_KEY,
        "filter": "hot",
        "public": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            items = response.json().get("results", [])
            result = []
            for item in items:
                link = item.get("url", "")
                if _is_published(link):
                    continue
                result.append({
                    "title": item.get("title", ""),
                    "summary": "",
                    "url": link,
                    "source": item.get("source", {}).get("domain", "CryptoPanic"),
                    "image_url": "",
                })
                if len(result) >= count:
                    break
            return result
    except Exception as e:
        logger.error(f"CryptoPanic error: {e}")
        return []


async def fetch_rss_news(count: int = 5) -> list[dict]:
    results = []
    for feed_url in RSS_FEEDS:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(feed_url, follow_redirects=True)
                feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                link = entry.get("link", "")
                if not link or _is_published(link):
                    continue

                summary_raw = entry.get("summary", "") or entry.get("description", "") or ""
                summary = BeautifulSoup(summary_raw, "lxml").get_text(separator=" ")[:300]

                image_url = ""
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url", "")
                elif hasattr(entry, "enclosures") and entry.enclosures:
                    image_url = entry.enclosures[0].get("href", "")

                results.append({
                    "title": entry.get("title", ""),
                    "summary": summary.strip(),
                    "url": link,
                    "source": feed.feed.get("title", feed_url),
                    "image_url": image_url,
                })

                if len(results) >= count:
                    return results
        except Exception as e:
            logger.error(f"RSS feed error ({feed_url}): {e}")
            continue

    return results


async def fetch_latest_news(count: int = 5) -> list[dict]:
    articles: list[dict] = []

    rss = await fetch_rss_news(count)
    articles.extend(rss)

    if len(articles) < count:
        cp = await fetch_cryptopanic_news(count - len(articles))
        articles.extend(cp)

    if len(articles) < count:
        na = await fetch_newsapi_articles(count=count - len(articles))
        articles.extend(na)

    return articles[:count]


def format_news_message(article: dict) -> str:
    title = article.get("title", "Без заголовка")
    summary = article.get("summary", "")
    url = article.get("url", "")
    source = article.get("source", "")

    text = f"📰 *{title}*\n\n"
    if summary:
        text += f"{summary}\n\n"
    if source:
        text += f"🔗 _Источник: {source}_\n"
    if url:
        text += f"[Читать подробнее]({url})"
    return text


def mark_article_published(article: dict) -> None:
    url = article.get("url", "")
    if url:
        _mark_published(url)
