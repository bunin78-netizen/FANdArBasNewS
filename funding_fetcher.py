"""
Fetches perpetual futures funding rates from Binance & OKX.
No API key required — public endpoints.
"""

import logging
import httpx
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BINANCE_PREMIUM_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
OKX_FUNDING_URL = "https://www.okx.com/api/v5/public/funding-rate"

BINANCE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "LTCUSDT", "NEARUSDT", "ATOMUSDT", "UNIUSDT",
]

OKX_SYMBOLS = [
    "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XRP-USDT-SWAP",
    "DOGE-USDT-SWAP", "ADA-USDT-SWAP", "AVAX-USDT-SWAP", "LINK-USDT-SWAP",
    "DOT-USDT-SWAP", "LTC-USDT-SWAP", "NEAR-USDT-SWAP", "ATOM-USDT-SWAP",
    "SUI-USDT-SWAP", "OP-USDT-SWAP", "ARB-USDT-SWAP",
]


def _parse_rate(rate_str: str | float) -> float:
    if isinstance(rate_str, str):
        return float(rate_str)
    return float(rate_str)


def _annualized(rate: float) -> float:
    """Convert 8h funding rate to annualized percentage."""
    return rate * 3 * 365 * 100


def _ticker_from_okx(inst_id: str) -> str:
    return inst_id.replace("-USDT-SWAP", "")


async def fetch_binance_rates() -> list[dict]:
    """Fetch funding rates from Binance Futures."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(BINANCE_PREMIUM_URL)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"Binance funding fetch failed: {e}")
        return []

    symbol_map = {item["symbol"]: item for item in data}
    result = []

    for sym in BINANCE_SYMBOLS:
        item = symbol_map.get(sym)
        if not item:
            continue
        try:
            rate = float(item.get("lastFundingRate", 0))
            next_ts = int(item.get("nextFundingTime", 0))
            mark_price = float(item.get("markPrice", 0))
            next_dt = datetime.fromtimestamp(next_ts / 1000, tz=timezone.utc) if next_ts else None

            ticker = sym.replace("USDT", "")
            result.append({
                "symbol": ticker,
                "exchange": "Binance",
                "rate": rate,
                "rate_pct": rate * 100,
                "annualized_pct": _annualized(rate),
                "mark_price": mark_price,
                "next_funding_time": next_dt,
            })
        except Exception as e:
            logger.warning(f"Binance parse fail {sym}: {e}")
            continue

    return result


async def fetch_okx_rates() -> list[dict]:
    """Fetch funding rates from OKX."""
    result = []
    async with httpx.AsyncClient(timeout=30) as client:
        for sym in OKX_SYMBOLS:
            try:
                resp = await client.get(f"{OKX_FUNDING_URL}?instId={sym}")
                resp.raise_for_status()
                body = resp.json()
                if body.get("code") != "0" or not body.get("data"):
                    continue
                item = body["data"][0]
                rate = _parse_rate(item.get("fundingRate", "0"))
                next_ts = int(item.get("fundingTime", 0))
                next_dt = datetime.fromtimestamp(next_ts / 1000, tz=timezone.utc) if next_ts else None

                result.append({
                    "symbol": _ticker_from_okx(sym),
                    "exchange": "OKX",
                    "rate": rate,
                    "rate_pct": rate * 100,
                    "annualized_pct": _annualized(rate),
                    "mark_price": 0,
                    "next_funding_time": next_dt,
                })
            except Exception as e:
                logger.warning(f"OKX parse fail {sym}: {e}")
                continue
    return result


async def fetch_funding_rates() -> list[dict]:
    """Returns combined funding rates from Binance + OKX, sorted by abs(rate)."""
    binance = await fetch_binance_rates()
    okx = await fetch_okx_rates()
    combined = binance + okx
    combined.sort(key=lambda x: abs(x["rate"]), reverse=True)
    return combined


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
