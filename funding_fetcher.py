"""
Fetches perpetual futures funding rates from Binance.
No API key required — public endpoint.
"""

import logging
import httpx
from datetime import datetime, timezone

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
