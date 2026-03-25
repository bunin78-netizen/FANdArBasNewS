# 🤖 Crypto Info & Promo Bot

Информационный Telegram-бот для публикации крипто-новостей, цен и рекламы торгового терминала.

## Возможности

- 📊 Цены топ монет (CoinGecko, бесплатно)
- 🌍 Глобальный обзор рынка
- 🔥 Трендовые монеты
- 📰 Новости из RSS (CoinTelegraph, Decrypt, CoinDesk, Bitcoin Magazine) + NewsAPI + CryptoPanic
- 💼 Реклама торгового терминала — inline-кнопка под каждым сообщением
- ⏰ Автопостинг цен, новостей и промо по расписанию

---

## Быстрый старт

```bash
cd crypto-telegram-bot
pip install -r requirements.txt
cp .env.example .env
nano .env        # заполни свои данные
python bot.py
```

---

## Настройка `.env`

| Переменная | Обязательна | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Токен от [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHANNEL_ID` | ✅ | ID канала для автопостинга (`@channel` или `-100...`) |
| `ADMIN_USER_IDS` | ✅ | Telegram user ID администраторов через запятую |
| `PROMO_TERMINAL_NAME` | ✅ | Название рекламируемого терминала |
| `PROMO_LINK` | ✅ | Реферальная / промо ссылка |
| `PROMO_SLOGAN` | — | Короткий слоган под названием терминала |
| `PROMO_INTERVAL_MINUTES` | — | Интервал авторекламы в минутах (0 = выкл) |
| `NEWS_INTERVAL_MINUTES` | — | Интервал автоновостей (по умолч. 60 мин) |
| `PRICE_INTERVAL_MINUTES` | — | Интервал автоцен (по умолч. 30 мин) |
| `TOP_COINS_COUNT` | — | Кол-во монет в сводке (по умолч. 10) |
| `NEWS_API_KEY` | — | [NewsAPI](https://newsapi.org) — бесплатный ключ |
| `CRYPTOPANIC_API_KEY` | — | [CryptoPanic](https://cryptopanic.com/developers/api/) — опционально |
| `COINGECKO_API_KEY` | — | CoinGecko Pro — опционально, без него работает free API |

---

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие + кнопка терминала |
| `/prices` | Топ монет с ценами |
| `/market` | Глобальный обзор рынка |
| `/trending` | Трендовые монеты |
| `/news` | Последние новости |
| `/coin <id>` | Детали по монете (напр. `/coin bitcoin`) |
| `/promo` | Реклама торгового терминала |
| `/publish_prices` | Опубликовать цены в канал _(admin)_ |
| `/publish_news` | Опубликовать новости в канал _(admin)_ |
| `/publish_promo` | Опубликовать рекламу в канал _(admin)_ |

---

## Структура проекта

```
crypto-telegram-bot/
├── bot.py            # Точка входа, все команды и хендлеры
├── config.py         # Конфигурация из .env
├── crypto_data.py    # Данные CoinGecko (цены, рынок, тренды)
├── news_fetcher.py   # Новости (RSS, NewsAPI, CryptoPanic)
├── scheduler.py      # Планировщик автопостинга
├── requirements.txt
├── .env.example
└── README.md
```
