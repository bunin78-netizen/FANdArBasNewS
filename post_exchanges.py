"""
One-shot script: post exchange referral links to Telegram channel.
Runs via GitHub Actions exchange_promo.yml every 3 days.
"""

import asyncio
import config
import exchanges as exch_data
import image_generator as imggen
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup


async def main():
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    exchanges = exch_data.EXCHANGES
    image = imggen.generate_exchanges_image(exchanges)
    caption = "🏛 Биржи с регистрацией через нас — бонус новым пользователям!"
    buttons = [
        [InlineKeyboardButton(f"{ex['emoji']} {ex['name']}", url=ex['url'])]
        for ex in exchanges
    ]
    await bot.send_photo(
        chat_id=config.TELEGRAM_CHANNEL_ID,
        photo=image,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    print(f"Posted exchange referrals ({len(exchanges)} exchanges).")
    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
