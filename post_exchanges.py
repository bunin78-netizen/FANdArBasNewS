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
    lines = ["🏛 <b>Биржи — регистрируйтесь с бонусом!</b>\n"]
    for ex in exchanges:
        eid = ex.get("custom_emoji_id")
        fb  = ex.get("emoji", "")
        icon = f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>' if eid else fb
        lines.append(f"{icon} <b>{ex['name']}</b> — {ex['bonus']}")
    caption = "\n".join(lines)
    row, rows = [], []
    for ex in exchanges:
        row.append(InlineKeyboardButton(f"{ex['emoji']} {ex['name']}", url=ex['url']))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    await bot.send_photo(
        chat_id=config.TELEGRAM_CHANNEL_ID,
        photo=image,
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    print(f"Posted exchange referrals ({len(exchanges)} exchanges).")
    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
