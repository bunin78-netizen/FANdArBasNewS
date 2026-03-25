"""
Crypto Info & Promo Telegram Bot
- Publishes crypto prices, market data, trending coins and news WITH images
- Every post has a beautiful generated image or article photo
- Promo posts use real FUNDARBAS screenshots from promo_images/
- No external API server — informational/advertising bot only
"""

import logging

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
import crypto_data
import news_fetcher
import crypto_facts
import certik_fetcher
import funding_fetcher
import exchanges as exch_data
import image_generator as imggen
import scheduler as sched

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _promo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"🚀 Открыть {config.PROMO_TERMINAL_NAME}",
            url=config.PROMO_LINK,
        )]
    ])


def _promo_text() -> str:
    return (
        f"💼 *{config.PROMO_TERMINAL_NAME}*\n\n"
        f"_{config.PROMO_SLOGAN}_\n\n"
        f"🚀 Торгуй умнее — используй лучший инструмент!\n"
        f"👉 [Попробовать бесплатно]({config.PROMO_LINK})"
    )


def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id if update.effective_user else None
        if config.ADMIN_USER_IDS and user_id not in config.ADMIN_USER_IDS:
            await update.message.reply_text("⛔ У вас нет прав для этой команды.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"👋 *Привет! Я Crypto Info Bot.*\n\n"
        f"Слежу за крипторынком и делюсь актуальными новостями, ценами и аналитикой.\n\n"
        f"📋 *Доступные команды:*\n"
        f"/prices — Топ криптовалют по цене\n"
        f"/market — Глобальный обзор рынка\n"
        f"/trending — Трендовые монеты\n"
        f"/news — Последние новости\n"
        f"/coin <id> — Детали по монете\n"
        f"/promo — Наш торговый терминал\n"
        f"/help — Справка\n"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=_promo_keyboard(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Справка по командам:*\n\n"
        "*/prices* — Топ монет с ценами и изменением за 24ч\n"
        "*/market* — Общая капитализация, объём, доминирование BTC/ETH\n"
        "*/trending* — Трендовые монеты на CoinGecko\n"
        "*/news* — Последние крипто-новости\n"
        "*/coin <id>* — Детальная информация по монете\n"
        "  Примеры: `/coin bitcoin`, `/coin ethereum`, `/coin solana`\n"
        "*/promo* — Информация о нашем торговом терминале\n\n"
        "🤖 *Для администраторов:*\n"
        "*/publish\\_prices* — Опубликовать цены в канал\n"
        "*/publish\\_news* — Опубликовать новости в канал\n"
        "*/publish\\_promo* — Опубликовать рекламу в канал\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю новости безопасности...")
    articles = await certik_fetcher.fetch_security_news(count=3)
    if not articles:
        await msg.edit_text(
            "⚠️ Новостей безопасности не найдено. Попробуйте позже."
        )
        return
    await msg.delete()
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
                await update.message.reply_photo(
                    photo=image_url, caption=caption, reply_markup=keyboard
                )
                sent = True
            except Exception:
                pass
        if not sent:
            card = imggen.generate_security_image(article)
            await update.message.reply_photo(
                photo=card, caption=caption, reply_markup=keyboard
            )
        certik_fetcher.mark_published(url)


async def cmd_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fact = crypto_facts.get_random_fact()
    image = imggen.generate_fact_image(fact)
    caption = f"💡 {fact['emoji']} Крипто-факт\n\n{fact['text']}"[:1024]
    await update.message.reply_photo(
        photo=image,
        caption=caption,
        reply_markup=_promo_keyboard(),
    )


async def cmd_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    image = imggen.get_promo_image() or imggen.generate_promo_card()
    caption = f"💼 {config.PROMO_TERMINAL_NAME}\n{config.PROMO_SLOGAN}\n\n👉 {config.PROMO_LINK}"
    await update.message.reply_photo(
        photo=image,
        caption=caption,
        reply_markup=_promo_keyboard(),
    )


async def cmd_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю данные о ценах...")
    coins = await crypto_data.fetch_top_coins(config.TOP_COINS_COUNT)
    image = imggen.generate_price_image(coins)
    caption = f"📊 Топ {len(coins)} криптовалют по капитализации\nДанные: CoinGecko  ·  {config.PROMO_TERMINAL_NAME}"
    await msg.delete()
    await update.message.reply_photo(
        photo=image,
        caption=caption,
        reply_markup=_promo_keyboard(),
    )


async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю данные рынка...")
    data = await crypto_data.fetch_global_market()
    image = imggen.generate_market_image(data or {})
    mcap = data.get("total_market_cap", {}).get("usd", 0) if data else 0
    change = data.get("market_cap_change_percentage_24h_usd", 0) if data else 0
    caption = (
        f"🌍 Глобальный крипторынок\n"
        f"Капитализация: {crypto_data._format_large_number(mcap)}  ·  24ч: {change:+.2f}%\n"
        f"Данные: CoinGecko  ·  {config.PROMO_TERMINAL_NAME}"
    )
    await msg.delete()
    await update.message.reply_photo(
        photo=image,
        caption=caption,
        reply_markup=_promo_keyboard(),
    )


async def cmd_trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю трендовые монеты...")
    trending = await crypto_data.fetch_trending()
    image = imggen.generate_trending_image(trending)
    caption = f"🔥 Топ трендовых монет сегодня\nДанные: CoinGecko  ·  {config.PROMO_TERMINAL_NAME}"
    await msg.delete()
    await update.message.reply_photo(
        photo=image,
        caption=caption,
        reply_markup=_promo_keyboard(),
    )


def _exchange_keyboard(exchanges: list) -> InlineKeyboardMarkup:
    """Build a 3-column icon grid of exchange buttons."""
    row, rows = [], []
    for i, ex in enumerate(exchanges):
        row.append(InlineKeyboardButton(f"{ex['emoji']} {ex['name']}", url=ex['url']))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _exchanges_caption(exchanges: list) -> str:
    lines = ["🏛 <b>Биржи — регистрируйтесь с бонусом!</b>\n"]
    for ex in exchanges:
        eid = ex.get("custom_emoji_id")
        fb  = ex.get("emoji", "")
        icon = f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>' if eid else fb
        lines.append(f"{icon} <b>{ex['name']}</b> — {ex['bonus']}")
    return "\n".join(lines)


async def cmd_exchanges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    exchanges = exch_data.EXCHANGES
    image = imggen.generate_exchanges_image(exchanges)
    await update.message.reply_photo(
        photo=image,
        caption=_exchanges_caption(exchanges),
        parse_mode="HTML",
        reply_markup=_exchange_keyboard(exchanges),
    )


async def cmd_funding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю ставки фандинга...")
    rates = await funding_fetcher.fetch_funding_rates()
    if not rates:
        await msg.edit_text("⚠️ Данные фандинга временно недоступны. Попробуйте позже.")
        return
    image = imggen.generate_funding_image(rates)
    top = rates[0] if rates else {}
    prefix = "+" if top.get("rate_pct", 0) >= 0 else ""
    caption = (
        f"📈 Ставки фандинга  ·  Перп. фьючерсы\n"
        f"Лидер: {top.get('symbol','')} {prefix}{top.get('rate_pct',0):.4f}%  ·  "
        f"Годовых: {top.get('annualized_pct',0):+.1f}%\n"
        f"Источник: Binance Futures  ·  {config.PROMO_TERMINAL_NAME}"
    )[:1024]
    await msg.delete()
    await update.message.reply_photo(
        photo=image,
        caption=caption,
        reply_markup=_promo_keyboard(),
    )


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Загружаю новости...")
    articles = await news_fetcher.fetch_latest_news(count=5)
    if not articles:
        await msg.edit_text("⚠️ Новости временно недоступны. Попробуйте позже.")
        return
    await msg.delete()
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
                await update.message.reply_photo(
                    photo=image_url,
                    caption=caption,
                    reply_markup=keyboard,
                )
                sent = True
            except Exception as e:
                logger.warning(f"Article image_url failed ({e}), generating card")
        if not sent:
            card = imggen.generate_news_card(article)
            try:
                await update.message.reply_photo(
                    photo=card,
                    caption=caption,
                    reply_markup=keyboard,
                )
            except Exception as e:
                logger.error(f"Failed to send news card: {e}")


async def cmd_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Укажите ID монеты. Пример: `/coin bitcoin`", parse_mode="Markdown"
        )
        return
    coin_id = context.args[0].lower()
    msg = await update.message.reply_text(
        f"⏳ Загружаю данные по *{coin_id}*...", parse_mode="Markdown"
    )
    data = await crypto_data.fetch_coin_detail(coin_id)
    if not data:
        await msg.edit_text(
            f"⚠️ Монета `{coin_id}` не найдена. Проверьте ID на CoinGecko.",
            parse_mode="Markdown",
        )
        return

    md = data.get("market_data", {})
    price = md.get("current_price", {}).get("usd", 0)
    change_24h = md.get("price_change_percentage_24h", 0) or 0
    change_7d = md.get("price_change_percentage_7d", 0) or 0
    mcap = md.get("market_cap", {}).get("usd", 0)
    volume = md.get("total_volume", {}).get("usd", 0)
    ath = md.get("ath", {}).get("usd", 0)
    atl = md.get("atl", {}).get("usd", 0)
    supply = md.get("circulating_supply", 0) or 0
    rank = data.get("market_cap_rank", "N/A")
    name = data.get("name", coin_id)
    symbol = data.get("symbol", "").upper()

    arrow_24h = "🟢 ▲" if change_24h >= 0 else "🔴 ▼"
    arrow_7d = "🟢 ▲" if change_7d >= 0 else "🔴 ▼"
    price_str = f"${price:,.2f}" if price >= 1 else f"${price:.8f}"

    c24_sign = "+" if change_24h >= 0 else ""
    caption = (
        f"🪙 {name} ({symbol})  Rank #{rank}\n"
        f"Price: {price_str}  ·  24h: {c24_sign}{change_24h:.2f}%\n"
        f"CoinGecko  ·  {config.PROMO_TERMINAL_NAME}"
    )
    image = imggen.generate_coin_image(data)
    await msg.delete()
    await update.message.reply_photo(
        photo=image,
        caption=caption,
        reply_markup=_promo_keyboard(),
    )


@admin_only
async def cmd_publish_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Публикую цены в канал...")
    coins = await crypto_data.fetch_top_coins(config.TOP_COINS_COUNT)
    image = imggen.generate_price_image(coins)
    caption = f"📊 Топ {len(coins)} криптовалют по капитализации\nДанные: CoinGecko  ·  {config.PROMO_TERMINAL_NAME}"
    try:
        await context.bot.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=image,
            caption=caption,
            reply_markup=_promo_keyboard(),
        )
        await msg.edit_text("✅ Цены успешно опубликованы в канал.")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка публикации: {e}")


@admin_only
async def cmd_publish_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Публикую новости в канал...")
    articles = await news_fetcher.fetch_latest_news(count=3)
    if not articles:
        await msg.edit_text("⚠️ Нет новых статей для публикации.")
        return
    count = 0
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
                await context.bot.send_photo(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    photo=image_url,
                    caption=caption,
                    reply_markup=keyboard,
                )
                sent = True
            except Exception as e:
                logger.warning(f"Article image_url failed ({e}), generating card")
        if not sent:
            card = imggen.generate_news_card(article)
            try:
                await context.bot.send_photo(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    photo=card,
                    caption=caption,
                    reply_markup=keyboard,
                )
            except Exception as e:
                logger.error(f"Failed to publish news card: {e}")
                continue
        news_fetcher.mark_article_published(article)
        count += 1
    await msg.edit_text(f"✅ Опубликовано {count} статей в канал.")


@admin_only
async def cmd_publish_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Публикую рекламу в канал...")
    image = imggen.get_promo_image() or imggen.generate_promo_card()
    caption = f"💼 {config.PROMO_TERMINAL_NAME}\n{config.PROMO_SLOGAN}\n\n👉 {config.PROMO_LINK}"
    try:
        await context.bot.send_photo(
            chat_id=config.TELEGRAM_CHANNEL_ID,
            photo=image,
            caption=caption,
            reply_markup=_promo_keyboard(),
        )
        await msg.edit_text("✅ Реклама опубликована в канал.")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка публикации: {e}")


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Неизвестная команда. Используйте /help для списка команд."
    )


async def post_init(application: Application):
    commands = [
        BotCommand("start", "Старт и приветствие"),
        BotCommand("help", "Справка по командам"),
        BotCommand("prices", "Топ криптовалют по цене"),
        BotCommand("market", "Глобальный обзор рынка"),
        BotCommand("trending", "Трендовые монеты"),
        BotCommand("news", "Последние новости"),
        BotCommand("coin", "Детали по монете (пример: /coin bitcoin)"),
        BotCommand("security", "Новости безопасности CertiK & SlowMist"),
        BotCommand("exchanges", "Биржи с бонусом при регистрации"),
        BotCommand("funding", "Ставки фандинга перп. фьючерсов"),
        BotCommand("fact", "Интересный факт о криптовалютах"),
        BotCommand("promo", "Наш торговый терминал"),
        BotCommand("publish_prices", "Опубликовать цены в канал [admin]"),
        BotCommand("publish_news", "Опубликовать новости в канал [admin]"),
        BotCommand("publish_promo", "Опубликовать рекламу в канал [admin]"),
    ]
    await application.bot.set_my_commands(commands)
    sched.set_bot(application.bot)
    sched.start_scheduler()
    logger.info("Bot commands registered. Scheduler started.")


async def post_shutdown(application: Application):
    sched.stop_scheduler()


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")
    if not config.TELEGRAM_CHANNEL_ID:
        logger.warning("TELEGRAM_CHANNEL_ID is not set — auto-publishing will not work.")

    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("promo", cmd_promo))
    application.add_handler(CommandHandler("prices", cmd_prices))
    application.add_handler(CommandHandler("market", cmd_market))
    application.add_handler(CommandHandler("trending", cmd_trending))
    application.add_handler(CommandHandler("news", cmd_news))
    application.add_handler(CommandHandler("security", cmd_security))
    application.add_handler(CommandHandler("exchanges", cmd_exchanges))
    application.add_handler(CommandHandler("funding", cmd_funding))
    application.add_handler(CommandHandler("fact", cmd_fact))
    application.add_handler(CommandHandler("coin", cmd_coin))
    application.add_handler(CommandHandler("publish_prices", cmd_publish_prices))
    application.add_handler(CommandHandler("publish_news", cmd_publish_news))
    application.add_handler(CommandHandler("publish_promo", cmd_publish_promo))
    application.add_handler(MessageHandler(filters.COMMAND, handle_unknown))

    logger.info("Starting Telegram bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
