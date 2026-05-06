"""
Arbitrage data module.
Fetches cross-exchange spot prices and builds arbitrage digest.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

# Top coins to track for exchange spreads
TOP_COINS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK", "DOT", "NEAR"]

# Exchange spot price endpoints
EXCHANGES_SPOT = {
    "Binance": lambda sym: f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDT",
    "Bybit": lambda sym: f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={sym}USDT",
    "OKX": lambda sym: f"https://www.okx.com/api/v5/market/ticker?instId={sym}-USDT",
}


async def _fetch_binance(sym: str) -> float | None:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(EXCHANGES_SPOT["Binance"](sym))
            r.raise_for_status()
            return float(r.json()["price"])
    except Exception as e:
        logger.debug(f"Binance {sym}: {e}")
        return None


async def _fetch_bybit(sym: str) -> float | None:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(EXCHANGES_SPOT["Bybit"](sym))
            r.raise_for_status()
            data = r.json()
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                return float(data["result"]["list"][0]["lastPrice"])
    except Exception as e:
        logger.debug(f"Bybit {sym}: {e}")
    return None


async def _fetch_okx(sym: str) -> float | None:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(EXCHANGES_SPOT["OKX"](sym))
            r.raise_for_status()
            data = r.json()
            if data.get("code") == "0" and data.get("data"):
                return float(data["data"][0]["last"])
    except Exception as e:
        logger.debug(f"OKX {sym}: {e}")
    return None


_FETCHERS = {
    "Binance": _fetch_binance,
    "Bybit": _fetch_bybit,
    "OKX": _fetch_okx,
}


async def fetch_exchange_prices() -> dict[str, dict[str, float | None]]:
    """Returns {coin: {exchange: price}} for all tracked coins/exchanges."""
    result = {}
    for coin in TOP_COINS:
        coin_data = {}
        for exch_name, fetcher in _FETCHERS.items():
            price = await fetcher(coin)
            if price:
                coin_data[exch_name] = price
        if coin_data:
            result[coin] = coin_data
    return result


def _spread_pct(best: float, worst: float) -> float:
    """Spread as % of best price."""
    if best == 0:
        return 0
    return ((worst - best) / best) * 100


def build_spread_summary(prices: dict[str, dict[str, float | None]]) -> list[dict]:
    """
    Returns list of dicts with spread data per coin:
    {symbol, best_exchange, best_price, worst_exchange, worst_price, spread_pct}
    """
    summary = []
    for coin, exch_data in prices.items():
        valid = {k: v for k, v in exch_data.items() if v is not None}
        if len(valid) < 2:
            continue
        best_ex = min(valid, key=valid.get)
        worst_ex = max(valid, key=valid.get)
        best_p = valid[best_ex]
        worst_p = valid[worst_ex]
        spread = _spread_pct(best_p, worst_p)
        summary.append({
            "symbol": coin,
            "best_exchange": best_ex,
            "best_price": best_p,
            "worst_exchange": worst_ex,
            "worst_price": worst_p,
            "spread_pct": spread,
        })
    summary.sort(key=lambda x: x["spread_pct"], reverse=True)
    return summary


def build_arbitrage_digest(
    all_rates: list[dict],
    spread_summary: list[dict],
) -> str:
    """
    Build a text digest for the daily arbitrage post.
    Includes top funding rates (positive & negative), best spreads.
    """
    lines = [
        "📊 *Арбитражный дайджест*",
        "Фандинг перп. фьючерсов + спреды бирж\n",
    ]

    # ── Best positive funding (expensive shorts) ──
    pos_rates = sorted(
        [r for r in all_rates if r["rate_pct"] > 0.005],
        key=lambda x: x["rate_pct"], reverse=True,
    )[:5]
    if pos_rates:
        lines.append("🔴 *Дорогой шорт (высокий фандинг)*")
        for r in pos_rates:
            ann = r["annualized_pct"]
            sign = "+" if ann >= 0 else ""
            lines.append(
                f"  {r['exchange']} {r['symbol']}: "
                f"`{r['rate_pct']:.4f}%` → годовых `{sign}{ann:.1f}%`"
            )
        lines.append("")

    # ── Best negative funding (cheap longs / pays you) ──
    neg_rates = sorted(
        [r for r in all_rates if r["rate_pct"] < -0.005],
        key=lambda x: x["rate_pct"],
    )[:5]
    if neg_rates:
        lines.append("🟢 *Дёшевый лонг (отрицательный / тебе платят)*")
        for r in neg_rates:
            ann = r["annualized_pct"]
            lines.append(
                f"  {r['exchange']} {r['symbol']}: "
                f"`{r['rate_pct']:.4f}%` → годовых `{ann:.1f}%`"
            )
        lines.append("")

    # ── Exchange spreads ──
    if spread_summary:
        lines.append("💱 *Спреды между биржами (spot)*")
        for s in spread_summary[:5]:
            lines.append(
                f"  *{s['symbol']}*: "
                f"купить {s['best_exchange']} `${s['best_price']:,.2f}` · "
                f"продать {s['worst_exchange']} `${s['worst_price']:,.2f}` · "
                f"спред `{s['spread_pct']:.3f}%`"
            )
        lines.append("")

    # ── Summary ──
    lines.append("💡 *Совет дня*")
    if pos_rates:
        best_pos = pos_rates[0]
        lines.append(
            f"• Самая дорогая пара для шорта: "
            f"*{best_pos['symbol']}* на {best_pos['exchange']} "
            f"({best_pos['rate_pct']:.4f}%)"
        )
    if neg_rates:
        best_neg = neg_rates[0]
        lines.append(
            f"• Лучшая пара для лонга (тебе платят): "
            f"*{best_neg['symbol']}* на {best_neg['exchange']} "
            f"({best_neg['rate_pct']:.4f}%)"
        )
    if spread_summary:
        top_spread = spread_summary[0]
        lines.append(
            f"• Максимальный спред: *{top_spread['symbol']}* — "
            f"{top_spread['spread_pct']:.3f}% между "
            f"{top_spread['best_exchange']} и {top_spread['worst_exchange']}"
        )

    return "\n".join(lines)
