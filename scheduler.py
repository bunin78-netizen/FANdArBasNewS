import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
import crypto_data
import news_fetcher
import crypto_facts
import certik_fetcher
import funding_fetcher
import arbitrage
import image_generator as imggen

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()
_bot_instance = None


def set_bot(bot):
    global _bot_instance
    _bot_instance = bot


async def _auto_publish_news():
    if _bot_instance is None:
        return
    logger.info("Auto-publishing news...")
    articles = await news_fetcher.fetch_latest_news(count=1)
    if not articles:
        return
    article = articles[0]
    image_url = article.get("image_url", "")
    title = article.get("title", "")[:200]
    source = article.get("source", "")
    url = article.get("url", "")
    caption = f"📰 {title}\n\n🔗 {source}\n{url}"[:1024]
    sent = False
    if image_url:
        try:
            await _bot_instance.send_photo(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                photo=image_url,
                caption=caption,
            )
            sent = True
        except Exception as e:
            logger.warning(f"image_url failed ({e}), generating card")
    if not sent:
        card = imggen.generate_news_card(article)
        try:
            await _bot_instance.send_photo(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                photo=card,
                caption=caption,
            )
        except Exception as e:
            logger.error(f"Failed to auto-publish news card: {e}")
            return
    news_fetcher.mark_article_published(article)


async def _auto_publish_security():
    if _bot_instance is None:
        return
    logger.info("Auto-publishing security news...")
    articles = await certik_fetcher.fetch_security_news(count=1)
    if not articles:
        return
    article = articles[0]
    image_url = article.get("image_url", "")
    title = article.get("title", "")[:200]
    source = article.get("source", "")
    url = article.get("url", "")
    caption = f"🔐 {title}\n\n📌 {source}\n{url}"[:1024]
    sent = False
    if image_url:
        try:
            await _bot_instance.send_photo(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                photo=image_url,
                caption=caption,
            )
            sent = True
        except Exception as e:
            logger.warning(f"Security image_url failed ({e}), generating card")
    if not sent:
        card = imggen.generate_security_image(article)
        try:
            await _bot_instance.send_photo(
                chat_id=config.TELEGRAM_CHANNEL_ID,
                photo=card,
                caption=caption,
            )
        except Exception as e:
            logger.error(f"Failed to auto-publish security card: {e}")
            return
    certik_fetcher.mark_published(url)


async def _auto_publish_fact():
    if _bot_instance is None:
        return
    logger.info("Auto-publishing crypto fact...")
    fact = crypto_facts.get_random_fact()
    image = imggen.generate_fact_image(fact)
    caption = f"💡 {fact['emoji']} Крипто-факт\n\n{fact['text']}"[:1024]
    try:
        await _bot_instance.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=image,
            caption=caption,
        )
    except Exception as e:
        logger.error(f"Failed to auto-publish fact: {e}")


async def _auto_publish_funding():
    if _bot_instance is None:
        return
    logger.info("Auto-publishing funding rates...")
    rates = await funding_fetcher.fetch_funding_rates()
    if not rates:
        return
    image = imggen.generate_funding_image(rates)
    top = rates[0] if rates else {}
    prefix = "+" if top.get("rate_pct", 0) >= 0 else ""
    caption = (
        f"📈 Ставки фандинга  ·  Перп. фьючерсы\n"
        f"Лидер: {top.get('symbol','')} {prefix}{top.get('rate_pct',0):.4f}%  ·  "
        f"Годовых: {top.get('annualized_pct',0):+.1f}%\n"
        f"Источник: Binance · OKX  ·  {config.PROMO_TERMINAL_NAME}"
    )[:1024]
    try:
        await _bot_instance.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=image,
            caption=caption,
        )
    except Exception as e:
        logger.error(f"Failed to auto-publish funding: {e}")


async def _auto_publish_arbitrage_digest():
    """Daily arbitrage digest: funding rates + exchange spreads."""
    if _bot_instance is None:
        return
    logger.info("Auto-publishing arbitrage digest...")
    rates = await funding_fetcher.fetch_funding_rates()
    prices = await arbitrage.fetch_exchange_prices()
    spreads = arbitrage.build_spread_summary(prices)
    if not rates and not spreads:
        logger.warning("No arbitrage data available, skipping digest.")
        return
    image = imggen.generate_arbitrage_image(rates, spreads)
    caption = (
        f"📊 Ежедневный арбитражный дайджест\n"
        f"Фандинг Binance+OKX · Спреды Binance/Bybit/OKX\n"
        f"{config.PROMO_TERMINAL_NAME}"
    )[:1024]
    try:
        await _bot_instance.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=image,
            caption=caption,
        )
    except Exception as e:
        logger.error(f"Failed to auto-publish arbitrage digest: {e}")


async def _auto_publish_promo():
    if _bot_instance is None:
        return
    logger.info("Auto-publishing promo message...")
    slogan = config.next_slogan()
    image = imggen.get_promo_image(slogan=slogan) or imggen.generate_promo_card(slogan=slogan)
    caption = f"💼 {config.PROMO_TERMINAL_NAME}\n{slogan}\n\n👉 {config.PROMO_LINK}"
    try:
        await _bot_instance.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=image,
            caption=caption,
        )
    except Exception as e:
        logger.error(f"Failed to auto-publish promo: {e}")


def start_scheduler():
    now = datetime.now(timezone.utc)

    # 1. Arb digest — core arbitrage content, fires first
    if config.ARBITRAGE_INTERVAL_MINUTES > 0:
        _scheduler.add_job(
            _auto_publish_arbitrage_digest,
            trigger=IntervalTrigger(
                minutes=config.ARBITRAGE_INTERVAL_MINUTES,
                start_date=now + timedelta(minutes=5),
            ),
            id="auto_arbitrage",
            replace_existing=True,
        )

    # 2. Funding rates — update mid-cycle
    if config.FUNDING_INTERVAL_MINUTES > 0:
        _scheduler.add_job(
            _auto_publish_funding,
            trigger=IntervalTrigger(
                minutes=config.FUNDING_INTERVAL_MINUTES,
                start_date=now + timedelta(minutes=90),
            ),
            id="auto_funding",
            replace_existing=True,
        )

    # 3. News — once per cycle, wraps up
    if config.NEWS_INTERVAL_MINUTES > 0:
        _scheduler.add_job(
            _auto_publish_news,
            trigger=IntervalTrigger(
                minutes=config.NEWS_INTERVAL_MINUTES,
                start_date=now + timedelta(minutes=180),
            ),
            id="auto_news",
            replace_existing=True,
        )

    # 4. Crypto facts (optional)
    if config.FACT_INTERVAL_MINUTES > 0:
        _scheduler.add_job(
            _auto_publish_fact,
            trigger=IntervalTrigger(
                minutes=config.FACT_INTERVAL_MINUTES,
                start_date=now + timedelta(minutes=90),
            ),
            id="auto_fact",
            replace_existing=True,
        )

    # 5. Security news (optional)
    if config.SECURITY_INTERVAL_MINUTES > 0:
        _scheduler.add_job(
            _auto_publish_security,
            trigger=IntervalTrigger(
                minutes=config.SECURITY_INTERVAL_MINUTES,
                start_date=now + timedelta(minutes=90),
            ),
            id="auto_security",
            replace_existing=True,
        )

    # 6. Promo (disabled by default)
    if config.PROMO_INTERVAL_MINUTES > 0:
        _scheduler.add_job(
            _auto_publish_promo,
            trigger=IntervalTrigger(
                minutes=config.PROMO_INTERVAL_MINUTES,
                start_date=now + timedelta(minutes=180),
            ),
            id="auto_promo",
            replace_existing=True,
        )

    _scheduler.start()

    active = []
    if config.ARBITRAGE_INTERVAL_MINUTES > 0:
        active.append(f"📊 arb {config.ARBITRAGE_INTERVAL_MINUTES}m")
    if config.FUNDING_INTERVAL_MINUTES > 0:
        active.append(f"📈 funding {config.FUNDING_INTERVAL_MINUTES}m")
    if config.NEWS_INTERVAL_MINUTES > 0:
        active.append(f"📰 news {config.NEWS_INTERVAL_MINUTES}m")
    if config.FACT_INTERVAL_MINUTES > 0:
        active.append(f"💡 fact {config.FACT_INTERVAL_MINUTES}m")
    if config.SECURITY_INTERVAL_MINUTES > 0:
        active.append(f"🔐 security {config.SECURITY_INTERVAL_MINUTES}m")
    if config.PROMO_INTERVAL_MINUTES > 0:
        active.append(f"🚀 promo {config.PROMO_INTERVAL_MINUTES}m")

    logger.info(f"Scheduler started: {' · '.join(active) if active else 'none'}")


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
