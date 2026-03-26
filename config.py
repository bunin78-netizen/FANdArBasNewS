import itertools
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID: str = os.getenv("TELEGRAM_CHANNEL_ID", "")

_admin_ids = os.getenv("ADMIN_USER_IDS", "")
ADMIN_USER_IDS: list[int] = []
for _x in _admin_ids.split(","):
    _x = _x.strip()
    try:
        if _x:
            ADMIN_USER_IDS.append(int(_x))
    except ValueError:
        pass

COINGECKO_API_KEY: str = os.getenv("COINGECKO_API_KEY", "")
NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
CRYPTOPANIC_API_KEY: str = os.getenv("CRYPTOPANIC_API_KEY", "")

PROMO_TERMINAL_NAME: str = os.getenv("PROMO_TERMINAL_NAME", "Trading Terminal")
PROMO_LINK: str = os.getenv("PROMO_LINK", "https://example.com")
BOT_LINK: str = os.getenv("BOT_LINK", "https://t.me/FUNDARBv4_bot")
PROMO_SLOGAN: str = os.getenv("PROMO_SLOGAN", "Лучший помощник в межбиржевом арбитраже")

PROMO_SLOGANS: list[str] = [
    "FundArbas — умный арбитраж без лишнего шума.",
    "Находим спред. Считаем риск. Действуем точно.",
    "Спокойная автоматизация арбитража.",
    "Меньше шума — больше системности.",
    "Точные решения для рынка 24/7.",
]
_slogan_cycle = itertools.cycle(PROMO_SLOGANS)


def next_slogan() -> str:
    return next(_slogan_cycle)


PROMO_INTERVAL_MINUTES: int = int(os.getenv("PROMO_INTERVAL_MINUTES", "300"))

NEWS_INTERVAL_MINUTES: int = int(os.getenv("NEWS_INTERVAL_MINUTES", "300"))
PRICE_INTERVAL_MINUTES: int = int(os.getenv("PRICE_INTERVAL_MINUTES", "10080"))
FACT_INTERVAL_MINUTES: int = int(os.getenv("FACT_INTERVAL_MINUTES", "360"))
SECURITY_INTERVAL_MINUTES: int = int(os.getenv("SECURITY_INTERVAL_MINUTES", "360"))
FUNDING_INTERVAL_MINUTES: int = int(os.getenv("FUNDING_INTERVAL_MINUTES", "480"))
TOP_COINS_COUNT: int = int(os.getenv("TOP_COINS_COUNT", "10"))

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_PRO_BASE_URL = "https://pro-api.coingecko.com/api/v3"
NEWS_API_BASE_URL = "https://newsapi.org/v2"
CRYPTOPANIC_BASE_URL = "https://cryptopanic.com/api/v1"

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://coindesk.com/arc/outboundfeeds/rss/",
]
