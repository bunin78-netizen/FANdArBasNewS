"""
Security news fetcher:
  - CertiK Medium blog  (incident analyses, security research)
  - SlowMist Medium blog (blockchain security incidents)
  - CertiK Skynet public leaderboard scrape (top security scores)
"""

import httpx
import feedparser
import json
import logging
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_PUBLISHED_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "published_security.json"
)
_MAX_STORED = 1000

_published_urls: set[str] = set()


# ── Deduplication ─────────────────────────────────────────────────────────────

def _load_published() -> None:
    global _published_urls
    if os.path.exists(_PUBLISHED_FILE):
        try:
            with open(_PUBLISHED_FILE, "r", encoding="utf-8") as f:
                _published_urls = set(json.load(f))
        except Exception:
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
        logger.warning(f"Could not save security published URLs: {e}")


def _is_published(url: str) -> bool:
    return url in _published_urls


def mark_published(url: str) -> None:
    _published_urls.add(url)
    _save_published()


# ── CertiK Medium feed ────────────────────────────────────────────────────────

CERTIK_FEED = "https://certik.medium.com/feed"
SLOWMIST_FEED = "https://slowmist.medium.com/feed"

# Keywords that make an article extra relevant for security/incident posts
_SECURITY_KEYWORDS = [
    "incident", "hack", "exploit", "attack", "vulnerability", "breach",
    "rug pull", "phishing", "audit", "security", "stolen", "flash loan",
    "re-entrancy", "reentrancy", "defi", "smart contract", "analysis",
    "post-mortem", "postmortem", "investigation", "scam", "fraud",
]


def _score_article(title: str, summary: str) -> int:
    """Simple relevance score — higher means more security-relevant."""
    text = (title + " " + summary).lower()
    return sum(1 for kw in _SECURITY_KEYWORDS if kw in text)


async def _fetch_medium_feed(feed_url: str, count: int = 5) -> list[dict]:
    results = []
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(
                feed_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CryptoBot/1.0)"},
            )
            feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            link = entry.get("link", "")
            if not link or _is_published(link):
                continue

            # Extract clean summary from HTML content
            raw = (
                entry.get("summary", "")
                or entry.get("content", [{}])[0].get("value", "")
            )
            summary = BeautifulSoup(raw, "lxml").get_text(separator=" ").strip()
            summary = re.sub(r"\s+", " ", summary)[:400]

            # Pick image from content
            image_url = ""
            content_raw = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
            if content_raw:
                soup = BeautifulSoup(content_raw, "lxml")
                img = soup.find("img")
                if img:
                    image_url = img.get("src", "")

            source_name = feed.feed.get("title", feed_url.split("/")[2])

            results.append({
                "title": entry.get("title", "").strip(),
                "summary": summary,
                "url": link,
                "source": source_name,
                "image_url": image_url,
                "score": _score_article(entry.get("title", ""), summary),
                "published": entry.get("published", ""),
            })

            if len(results) >= count * 2:
                break

        # Sort by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:count]

    except Exception as e:
        logger.error(f"Medium feed error ({feed_url}): {e}")
        return []


# ── CertiK Skynet leaderboard (public page scrape) ───────────────────────────

async def fetch_skynet_leaderboard(top_n: int = 10) -> list[dict]:
    """
    Fetch top projects by security score from CertiK Skynet leaderboard page.
    Returns a list of dicts with name, score, label.
    Falls back to empty list if the page is not scrapeable.
    """
    url = "https://skynet.certik.com/leaderboards"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://skynet.certik.com/",
    }
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        # Try to find score data in Next.js __NEXT_DATA__ JSON
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if script and script.string:
            data = json.loads(script.string)
            # Navigate to leaderboard entries — path varies by build
            props = data.get("props", {}).get("pageProps", {})
            projects = props.get("projects", []) or props.get("leaderboard", [])
            results = []
            for p in projects[:top_n]:
                results.append({
                    "name": p.get("name", p.get("projectName", "Unknown")),
                    "score": p.get("securityScore", p.get("score", 0)),
                    "label": p.get("securityLabel", ""),
                    "audit_count": p.get("auditCount", 0),
                })
            if results:
                return results

        logger.info("Skynet leaderboard: NEXT_DATA path not found, returning empty")
        return []

    except Exception as e:
        logger.warning(f"Skynet leaderboard fetch failed: {e}")
        return []


# ── Combined fetcher ──────────────────────────────────────────────────────────

async def fetch_security_news(count: int = 3) -> list[dict]:
    """
    Fetch security news from CertiK and SlowMist, combined and deduped.
    Returns up to `count` most relevant unpublished articles.
    """
    certik = await _fetch_medium_feed(CERTIK_FEED, count=count + 2)
    slowmist = await _fetch_medium_feed(SLOWMIST_FEED, count=count + 2)

    combined: list[dict] = []
    seen: set[str] = set()
    for article in certik + slowmist:
        url = article["url"]
        if url not in seen and not _is_published(url):
            seen.add(url)
            combined.append(article)

    # Sort by relevance
    combined.sort(key=lambda x: x["score"], reverse=True)
    return combined[:count]


def format_security_message(article: dict) -> str:
    title = article.get("title", "Без заголовка")
    summary = article.get("summary", "")
    url = article.get("url", "")
    source = article.get("source", "")

    lines = [f"🔐 {title}"]
    if summary:
        lines.append(f"\n{summary[:300]}{'…' if len(summary) > 300 else ''}")
    if source:
        lines.append(f"\n📌 Источник: {source}")
    if url:
        lines.append(f"🔗 {url}")
    return "\n".join(lines)


_load_published()
