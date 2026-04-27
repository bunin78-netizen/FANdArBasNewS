"""
Fetches perpetual futures funding rates from Binance and CoinGlass.
No API key required for Binance — public endpoint.
CoinGlass requires COINGLASS_API_KEY (free tier available at coinglass.com).
"""

import logging
import httpx
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)

BINANCE_PREMIUM_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"

TRACKED_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "LTCUSDT", "NEARUSDT", "ATOMUSDT", "UNIUSDT",
]


async def fetch_funding_rates() -> list[dict]:
    """Returns funding rate data for tracked perpetual contracts."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(BINANCE_PREMIUM_URL)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch funding rates: {e}")
        return []

    symbol_map = {item["symbol"]: item for item in data}
    result = []

    for sym in TRACKED_SYMBOLS:
        item = symbol_map.get(sym)
        if not item:
            continue
        try:
            rate = float(item.get("lastFundingRate", 0))
            next_ts = int(item.get("nextFundingTime", 0))
            mark_price = float(item.get("markPrice", 0))
            next_dt = datetime.fromtimestamp(next_ts / 1000, tz=timezone.utc) if next_ts else None

            annualized = rate * 3 * 365 * 100

            ticker = sym.replace("USDT", "")
            result.append({
                "symbol": ticker,
                "full_symbol": sym,
                "rate": rate,
                "rate_pct": rate * 100,
                "annualized_pct": annualized,
                "mark_price": mark_price,
                "next_funding_time": next_dt,
            })
        except Exception as e:
            logger.warning(f"Failed to parse {sym}: {e}")
            continue

    result.sort(key=lambda x: abs(x["rate"]), reverse=True)
    return result


def funding_sentiment(rate_pct: float) -> str:
    """Returns emoji sentiment based on funding rate."""
    if rate_pct > 0.1:
        return "🔴"
    elif rate_pct > 0.03:
        return "🟠"
    elif rate_pct > 0:
        return "🟡"
    elif rate_pct > -0.03:
        return "🟢"
    else:
        return "🔵"


async def fetch_top_funding_coinglass(top_n: int = 5) -> list[dict]:
    """Returns top N perpetual funding rates by absolute value from CoinGlass.

    Each entry contains:
        symbol, exchange, rate_pct, annualized_pct
    Requires COINGLASS_API_KEY set in config / environment.
    Falls back to an empty list if the key is missing or the request fails.
    """
    api_key = config.COINGLASS_API_KEY
    if not api_key:
        logger.warning("COINGLASS_API_KEY not set — skipping CoinGlass funding fetch")
        return []

    url = f"{config.COINGLASS_BASE_URL}/funding"
    headers = {"coinglassSecret": api_key}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch CoinGlass funding rates: {e}")
        return []

    if payload.get("code") != "0" or not isinstance(payload.get("data"), list):
        logger.error(f"Unexpected CoinGlass response: {payload.get('msg', 'unknown error')}")
        return []

    entries: list[dict] = []
    for item in payload["data"]:
        symbol = item.get("symbol", "")
        for margin_list in (item.get("uMarginList") or [], item.get("cMarginList") or []):
            for ex in margin_list:
                try:
                    rate = float(ex.get("rate", 0) or 0)
                except (TypeError, ValueError):
                    continue
                exchange = ex.get("exchangeName", "")
                rate_pct = rate * 100
                annualized_pct = rate * 3 * 365 * 100
                entries.append({
                    "symbol": symbol,
                    "exchange": exchange,
                    "rate": rate,
                    "rate_pct": rate_pct,
                    "annualized_pct": annualized_pct,
                })

    entries.sort(key=lambda x: abs(x["rate"]), reverse=True)
    return entries[:top_n]
