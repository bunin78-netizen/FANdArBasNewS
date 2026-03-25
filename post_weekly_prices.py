"""
One-shot script: fetch top coins and post to Telegram channel.
Runs via GitHub Actions weekly_prices.yml every Monday at 09:00 UTC.
"""

import asyncio
import config
import crypto_data
import image_generator as imggen
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup


async def main():
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"🚀 {config.PROMO_TERMINAL_NAME}", url=config.PROMO_LINK)
    ]])
    coins = await crypto_data.fetch_top_coins(config.TOP_COINS_COUNT)
    if not coins:
        print("ERROR: failed to fetch coin data")
        await bot.close()
        return
    image = imggen.generate_price_image(coins)
    caption = (
        f"📊 Топ {len(coins)} криптовалют по капитализации\n"
        f"Данные: CoinGecko  ·  {config.PROMO_TERMINAL_NAME}"
    )
    await bot.send_photo(
        chat_id=config.TELEGRAM_CHANNEL_ID,
        photo=image,
        caption=caption,
        reply_markup=keyboard,
    )
    print(f"Posted top-{len(coins)} prices successfully.")
    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
