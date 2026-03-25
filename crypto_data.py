import httpx
import logging
from config import (
    COINGECKO_BASE_URL,
    COINGECKO_PRO_BASE_URL,
    COINGECKO_API_KEY,
    TOP_COINS_COUNT,
)

logger = logging.getLogger(__name__)

CHANGE_ARROW = {True: "🟢 ▲", False: "🔴 ▼"}


def _base_url() -> str:
    return COINGECKO_PRO_BASE_URL if COINGECKO_API_KEY else COINGECKO_BASE_URL


def _headers() -> dict:
    if COINGECKO_API_KEY:
        return {"x-cg-pro-api-key": COINGECKO_API_KEY}
    return {}


async def fetch_top_coins(limit: int = TOP_COINS_COUNT) -> list[dict]:
    url = f"{_base_url()}/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params, headers=_headers())
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching top coins: {e}")
        return []


async def fetch_coin_detail(coin_id: str) -> dict | None:
    url = f"{_base_url()}/coins/{coin_id}"
    params = {
        "localization": False,
        "tickers": False,
        "market_data": True,
        "community_data": False,
        "developer_data": False,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params, headers=_headers())
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching coin detail for {coin_id}: {e}")
        return None


async def fetch_global_market() -> dict | None:
    url = f"{_base_url()}/global"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=_headers())
            response.raise_for_status()
            return response.json().get("data", {})
    except Exception as e:
        logger.error(f"Error fetching global market data: {e}")
        return None


async def fetch_trending() -> list[dict]:
    url = f"{_base_url()}/search/trending"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=_headers())
            response.raise_for_status()
            return response.json().get("coins", [])
    except Exception as e:
        logger.error(f"Error fetching trending coins: {e}")
        return []


def format_price_message(coins: list[dict]) -> str:
    if not coins:
        return "⚠️ Не удалось получить данные о ценах."

    lines = ["📊 *Топ криптовалют по рыночной капитализации*\n"]
    for coin in coins:
        change = coin.get("price_change_percentage_24h") or 0
        arrow = CHANGE_ARROW[change >= 0]
        price = coin.get("current_price", 0)
        symbol = coin.get("symbol", "").upper()
        name = coin.get("name", "")
        mcap = coin.get("market_cap", 0)

        price_str = f"${price:,.2f}" if price >= 1 else f"${price:.6f}"
        mcap_str = _format_large_number(mcap)

        lines.append(
            f"{arrow} *{name}* ({symbol})\n"
            f"   💵 Цена: `{price_str}`\n"
            f"   📈 24ч: `{change:+.2f}%`\n"
            f"   🏦 Капитализация: `{mcap_str}`\n"
        )

    lines.append("\n🔄 _Данные: CoinGecko_")
    return "\n".join(lines)


def format_global_market_message(data: dict) -> str:
    if not data:
        return "⚠️ Не удалось получить данные рынка."

    total_mcap = data.get("total_market_cap", {}).get("usd", 0)
    total_volume = data.get("total_volume", {}).get("usd", 0)
    btc_dominance = data.get("market_cap_percentage", {}).get("btc", 0)
    eth_dominance = data.get("market_cap_percentage", {}).get("eth", 0)
    active_coins = data.get("active_cryptocurrencies", 0)
    mcap_change = data.get("market_cap_change_percentage_24h_usd", 0)
    arrow = CHANGE_ARROW[mcap_change >= 0]

    return (
        f"🌍 *Глобальный крипторынок*\n\n"
        f"💰 Общая капитализация: `{_format_large_number(total_mcap)}`\n"
        f"{arrow} Изменение 24ч: `{mcap_change:+.2f}%`\n"
        f"📦 Объём торгов 24ч: `{_format_large_number(total_volume)}`\n"
        f"🟡 Доминирование BTC: `{btc_dominance:.1f}%`\n"
        f"🔵 Доминирование ETH: `{eth_dominance:.1f}%`\n"
        f"🪙 Активных монет: `{active_coins:,}`\n\n"
        f"🔄 _Данные: CoinGecko_"
    )


def format_trending_message(trending: list[dict]) -> str:
    if not trending:
        return "⚠️ Не удалось получить данные о трендах."

    lines = ["🔥 *Трендовые криптовалюты сегодня*\n"]
    for i, item in enumerate(trending[:7], 1):
        coin = item.get("item", {})
        name = coin.get("name", "N/A")
        symbol = coin.get("symbol", "N/A").upper()
        rank = coin.get("market_cap_rank", "N/A")
        lines.append(f"{i}. *{name}* ({symbol}) — Ранг #{rank}")

    lines.append("\n🔄 _Данные: CoinGecko_")
    return "\n".join(lines)


def _format_large_number(n: float) -> str:
    if n >= 1_000_000_000_000:
        return f"${n / 1_000_000_000_000:.2f}T"
    elif n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    else:
        return f"${n:,.0f}"
