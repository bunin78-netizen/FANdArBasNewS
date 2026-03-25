import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
import crypto_data
import news_fetcher
import crypto_facts
import certik_fetcher
import image_generator as imggen

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()
_bot_instance = None


def set_bot(bot):
    global _bot_instance
    _bot_instance = bot


def _promo_text() -> str:
    return (
        f"💼 *{config.PROMO_TERMINAL_NAME}*\n\n"
        f"_{config.PROMO_SLOGAN}_\n\n"
        f"🚀 Торгуй умнее — используй лучший инструмент!\n"
        f"👉 [Попробовать бесплатно]({config.PROMO_LINK})"
    )


def _promo_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"🚀 Открыть {config.PROMO_TERMINAL_NAME}", url=config.PROMO_LINK)
    ]])


async def _auto_publish_prices():
    if _bot_instance is None:
        return
    logger.info("Auto-publishing price update...")
    coins = await crypto_data.fetch_top_coins(config.TOP_COINS_COUNT)
    if not coins:
        return
    image = imggen.generate_price_image(coins)
    caption = f"📊 Топ {len(coins)} криптовалют по капитализации\nДанные: CoinGecko  ·  {config.PROMO_TERMINAL_NAME}"
    try:
        await _bot_instance.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=image,
            caption=caption,
            reply_markup=_promo_keyboard(),
        )
    except Exception as e:
        logger.error(f"Failed to auto-publish prices: {e}")


async def _auto_publish_news():
    if _bot_instance is None:
        return
    logger.info("Auto-publishing news...")
    articles = await news_fetcher.fetch_latest_news(count=3)
    for i, article in enumerate(articles):
        text = news_fetcher.format_news_message(article)
        image_url = article.get("image_url", "")
        keyboard = _promo_keyboard() if i == len(articles) - 1 else None
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
                    reply_markup=keyboard,
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
                    reply_markup=keyboard,
                )
            except Exception as e:
                logger.error(f"Failed to auto-publish news card: {e}")
                continue
        news_fetcher.mark_article_published(article)


async def _auto_publish_security():
    if _bot_instance is None:
        return
    logger.info("Auto-publishing security news...")
    articles = await certik_fetcher.fetch_security_news(count=2)
    for i, article in enumerate(articles):
        image_url = article.get("image_url", "")
        title = article.get("title", "")[:200]
        source = article.get("source", "")
        url = article.get("url", "")
        caption = f"🔐 {title}\n\n📌 {source}\n{url}"[:1024]
        keyboard = _promo_keyboard() if i == len(articles) - 1 else None
        sent = False
        if image_url:
            try:
                await _bot_instance.send_photo(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    photo=image_url,
                    caption=caption,
                    reply_markup=keyboard,
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
                    reply_markup=keyboard,
                )
            except Exception as e:
                logger.error(f"Failed to auto-publish security card: {e}")
                continue
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
            reply_markup=_promo_keyboard(),
        )
    except Exception as e:
        logger.error(f"Failed to auto-publish fact: {e}")


async def _auto_publish_promo():
    if _bot_instance is None:
        return
    logger.info("Auto-publishing promo message...")
    image = imggen.get_promo_image() or imggen.generate_promo_card()
    caption = f"💼 {config.PROMO_TERMINAL_NAME}\n{config.PROMO_SLOGAN}\n\n👉 {config.PROMO_LINK}"
    try:
        await _bot_instance.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=image,
            caption=caption,
            reply_markup=_promo_keyboard(),
        )
    except Exception as e:
        logger.error(f"Failed to auto-publish promo: {e}")


def start_scheduler():
    _scheduler.add_job(
        _auto_publish_prices,
        trigger=IntervalTrigger(minutes=config.PRICE_INTERVAL_MINUTES),
        id="auto_prices",
        replace_existing=True,
    )
    _scheduler.add_job(
        _auto_publish_news,
        trigger=IntervalTrigger(minutes=config.NEWS_INTERVAL_MINUTES),
        id="auto_news",
        replace_existing=True,
    )
    _scheduler.add_job(
        _auto_publish_security,
        trigger=IntervalTrigger(minutes=config.SECURITY_INTERVAL_MINUTES),
        id="auto_security",
        replace_existing=True,
    )
    _scheduler.add_job(
        _auto_publish_fact,
        trigger=IntervalTrigger(minutes=config.FACT_INTERVAL_MINUTES),
        id="auto_fact",
        replace_existing=True,
    )
    if config.PROMO_INTERVAL_MINUTES > 0:
        _scheduler.add_job(
            _auto_publish_promo,
            trigger=IntervalTrigger(minutes=config.PROMO_INTERVAL_MINUTES),
            id="auto_promo",
            replace_existing=True,
        )
    _scheduler.start()
    logger.info(
        f"Scheduler started: prices every {config.PRICE_INTERVAL_MINUTES}m, "
        f"news every {config.NEWS_INTERVAL_MINUTES}m, "
        f"security every {config.SECURITY_INTERVAL_MINUTES}m, "
        f"facts every {config.FACT_INTERVAL_MINUTES}m, "
        f"promo every {config.PROMO_INTERVAL_MINUTES}m"
    )


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
