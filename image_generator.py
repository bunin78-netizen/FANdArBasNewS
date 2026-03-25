"""
Generates beautiful dark-themed images for every bot post.
Promo posts use real FUNDARBAS screenshots from the promo_images/ folder.
"""

import io
import os
import random
import textwrap
import logging
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

import config

logger = logging.getLogger(__name__)

PROMO_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "promo_images")

IMG_W = 800
PAD = 24

# Dark theme palette
C_BG     = (10, 14, 20)
C_CARD   = (20, 26, 36)
C_CARD2  = (16, 21, 30)
C_BORDER = (40, 52, 68)
C_TEXT   = (225, 235, 245)
C_MUTED  = (110, 125, 145)
C_GREEN  = (52, 199, 89)
C_RED    = (255, 69, 58)
C_ACCENT = (64, 156, 255)
C_GOLD   = (255, 196, 0)
C_HEADER = (14, 20, 32)


# ── Font loader ──────────────────────────────────────────────────────────────

_font_cache: dict[tuple, ImageFont.ImageFont] = {}

def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]

    bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]
    paths = bold_paths if bold else regular_paths
    for path in paths:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, size)
                _font_cache[key] = f
                return f
            except Exception:
                continue
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f


# ── Helpers ──────────────────────────────────────────────────────────────────

def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _fmt_price(p: float) -> str:
    if p >= 1000:
        return f"${p:,.2f}"
    elif p >= 1:
        return f"${p:.4f}"
    elif p >= 0.01:
        return f"${p:.5f}"
    else:
        return f"${p:.8f}"


def _fmt_big(n: float) -> str:
    if n >= 1e12:
        return f"${n/1e12:.2f}T"
    elif n >= 1e9:
        return f"${n/1e9:.2f}B"
    elif n >= 1e6:
        return f"${n/1e6:.2f}M"
    else:
        return f"${n:,.0f}"


def _draw_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str, h: int = 80):
    draw.rectangle([0, 0, IMG_W, h], fill=C_HEADER)
    draw.rectangle([0, h - 2, IMG_W, h], fill=C_BORDER)
    draw.text((PAD, 14), title, fill=C_ACCENT, font=_font(26, bold=True))
    draw.text((PAD, 48), subtitle, fill=C_MUTED, font=_font(14))
    brand = config.PROMO_TERMINAL_NAME
    bw = _text_w(draw, brand, _font(15, bold=True))
    draw.text((IMG_W - PAD - bw, 30), brand, fill=C_GOLD, font=_font(15, bold=True))


def _draw_footer(draw: ImageDraw.ImageDraw, img_h: int, source: str = "CoinGecko"):
    fy = img_h - 38
    draw.rectangle([0, fy, IMG_W, img_h], fill=C_HEADER)
    draw.rectangle([0, fy, IMG_W, fy + 1], fill=C_BORDER)
    draw.text((PAD, fy + 10), f"Data: {source}", fill=C_MUTED, font=_font(13))
    link_text = config.PROMO_LINK
    lw = _text_w(draw, link_text, _font(13))
    draw.text((IMG_W - PAD - lw, fy + 10), link_text, fill=C_GOLD, font=_font(13))


def _to_bytes(img: Image.Image, fmt: str = "PNG") -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format=fmt, optimize=True)
    buf.seek(0)
    buf.name = f"image.{fmt.lower()}"
    return buf


# ── Price image ──────────────────────────────────────────────────────────────

def generate_price_image(coins: list[dict]) -> io.BytesIO:
    HEADER_H = 82
    FOOTER_H = 40
    COL_H_ROW = 32
    ROW_H = 58
    n = len(coins)
    img_h = HEADER_H + COL_H_ROW + n * ROW_H + FOOTER_H + 10

    img = Image.new("RGB", (IMG_W, img_h), C_BG)
    draw = ImageDraw.Draw(img)

    ts = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")
    _draw_header(draw, "CRYPTO MARKET UPDATE", ts, HEADER_H)

    # Column header row
    cy = HEADER_H + 6
    col_labels = [("#", PAD), ("Name", PAD + 45), ("Price (USD)", PAD + 290),
                  ("24h %", PAD + 470), ("Market Cap", PAD + 590)]
    for label, x in col_labels:
        draw.text((x, cy), label, fill=C_MUTED, font=_font(13))
    cy += COL_H_ROW - 4
    draw.line([PAD, cy, IMG_W - PAD, cy], fill=C_BORDER, width=1)
    cy += 4

    for i, coin in enumerate(coins):
        ry = cy + i * ROW_H
        bg = C_CARD if i % 2 == 0 else C_CARD2
        draw.rectangle([0, ry - 2, IMG_W, ry + ROW_H - 4], fill=bg)

        change = coin.get("price_change_percentage_24h") or 0
        price  = coin.get("current_price", 0)
        symbol = coin.get("symbol", "").upper()
        name   = (coin.get("name", "")[:14]).strip()
        mcap   = coin.get("market_cap", 0)
        rank   = coin.get("market_cap_rank", i + 1)
        color  = C_GREEN if change >= 0 else C_RED
        prefix = "+" if change >= 0 else ""

        mid = ry + (ROW_H - 4) // 2 - 10
        draw.text((PAD, mid + 3), str(rank), fill=C_MUTED, font=_font(14))
        draw.text((PAD + 45, mid - 6), name, fill=C_TEXT, font=_font(17, bold=True))
        draw.text((PAD + 45, mid + 16), symbol, fill=C_MUTED, font=_font(13))
        draw.text((PAD + 290, mid + 3), _fmt_price(price), fill=C_TEXT, font=_font(16, bold=True))
        draw.text((PAD + 470, mid + 3), f"{prefix}{change:.2f}%", fill=color, font=_font(16, bold=True))
        draw.text((PAD + 590, mid + 3), _fmt_big(mcap), fill=C_TEXT, font=_font(15))

    _draw_footer(draw, img_h)
    return _to_bytes(img)


# ── Global market image ───────────────────────────────────────────────────────

def generate_market_image(data: dict) -> io.BytesIO:
    HEADER_H = 82
    FOOTER_H = 40
    img_h = HEADER_H + 340 + FOOTER_H

    img = Image.new("RGB", (IMG_W, img_h), C_BG)
    draw = ImageDraw.Draw(img)

    ts = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")
    _draw_header(draw, "GLOBAL CRYPTO MARKET", ts, HEADER_H)

    total_mcap  = data.get("total_market_cap", {}).get("usd", 0)
    total_vol   = data.get("total_volume", {}).get("usd", 0)
    btc_dom     = data.get("market_cap_percentage", {}).get("btc", 0)
    eth_dom     = data.get("market_cap_percentage", {}).get("eth", 0)
    active      = data.get("active_cryptocurrencies", 0)
    mcap_change = data.get("market_cap_change_percentage_24h_usd", 0) or 0

    stats = [
        ("Total Market Cap",   _fmt_big(total_mcap),   C_ACCENT),
        ("24h Change",         f"{'+'if mcap_change>=0 else ''}{mcap_change:.2f}%",
                               C_GREEN if mcap_change >= 0 else C_RED),
        ("24h Volume",         _fmt_big(total_vol),    C_TEXT),
        ("BTC Dominance",      f"{btc_dom:.1f}%",      C_GOLD),
        ("ETH Dominance",      f"{eth_dom:.1f}%",      (100, 160, 255)),
        ("Active Coins",       f"{active:,}",          C_TEXT),
    ]

    y = HEADER_H + 20
    card_w = (IMG_W - PAD * 2 - 16) // 2
    for idx, (label, value, color) in enumerate(stats):
        col = idx % 2
        row = idx // 2
        cx = PAD + col * (card_w + 16)
        cy = y + row * 100
        draw.rounded_rectangle([cx, cy, cx + card_w, cy + 82], radius=10, fill=C_CARD)
        draw.rounded_rectangle([cx, cy, cx + 4, cy + 82], radius=2, fill=color)
        draw.text((cx + 16, cy + 12), label, fill=C_MUTED, font=_font(14))
        draw.text((cx + 16, cy + 36), value, fill=color, font=_font(24, bold=True))

    _draw_footer(draw, img_h)
    return _to_bytes(img)


# ── Trending image ────────────────────────────────────────────────────────────

def generate_trending_image(trending: list[dict]) -> io.BytesIO:
    items = trending[:7]
    HEADER_H = 82
    FOOTER_H = 40
    ROW_H = 60
    img_h = HEADER_H + len(items) * ROW_H + 16 + FOOTER_H

    img = Image.new("RGB", (IMG_W, img_h), C_BG)
    draw = ImageDraw.Draw(img)

    ts = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")
    _draw_header(draw, "TRENDING COINS TODAY", ts, HEADER_H)

    y = HEADER_H + 10
    for i, item in enumerate(items):
        coin  = item.get("item", {})
        name  = coin.get("name", "N/A")[:20]
        sym   = coin.get("symbol", "N/A").upper()
        rank  = coin.get("market_cap_rank", "—")
        score = coin.get("score", i)

        ry = y + i * ROW_H
        bg = C_CARD if i % 2 == 0 else C_CARD2
        draw.rectangle([0, ry, IMG_W, ry + ROW_H - 2], fill=bg)

        num_text = f"{i+1}"
        draw.text((PAD, ry + 16), num_text, fill=C_GOLD, font=_font(22, bold=True))
        draw.text((PAD + 50, ry + 8), name, fill=C_TEXT, font=_font(18, bold=True))
        draw.text((PAD + 50, ry + 32), sym, fill=C_MUTED, font=_font(14))
        rank_text = f"Rank #{rank}"
        rw = _text_w(draw, rank_text, _font(15))
        draw.text((IMG_W - PAD - rw, ry + 20), rank_text, fill=C_ACCENT, font=_font(15))

    _draw_footer(draw, img_h)
    return _to_bytes(img)


# ── Single coin image ─────────────────────────────────────────────────────────

def generate_coin_image(data: dict) -> io.BytesIO:
    HEADER_H = 82
    FOOTER_H = 40
    img_h = HEADER_H + 400 + FOOTER_H

    img = Image.new("RGB", (IMG_W, img_h), C_BG)
    draw = ImageDraw.Draw(img)

    md     = data.get("market_data", {})
    name   = data.get("name", "")
    symbol = data.get("symbol", "").upper()
    rank   = data.get("market_cap_rank", "N/A")
    price  = md.get("current_price", {}).get("usd", 0)
    c24    = md.get("price_change_percentage_24h", 0) or 0
    c7d    = md.get("price_change_percentage_7d", 0) or 0
    mcap   = md.get("market_cap", {}).get("usd", 0)
    vol    = md.get("total_volume", {}).get("usd", 0)
    ath    = md.get("ath", {}).get("usd", 0)
    atl    = md.get("atl", {}).get("usd", 0)
    supply = md.get("circulating_supply", 0) or 0

    ts = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")
    _draw_header(draw, f"{name.upper()}  ({symbol})", f"Rank #{rank}  •  {ts}", HEADER_H)

    # Big price
    py = HEADER_H + 20
    price_str = _fmt_price(price)
    draw.text((PAD, py), price_str, fill=C_TEXT, font=_font(42, bold=True))
    c24_color = C_GREEN if c24 >= 0 else C_RED
    c24_str = f"{'+'if c24>=0 else ''}{c24:.2f}% (24h)"
    draw.text((PAD, py + 54), c24_str, fill=c24_color, font=_font(20, bold=True))
    c7d_color = C_GREEN if c7d >= 0 else C_RED
    c7d_str = f"{'+'if c7d>=0 else ''}{c7d:.2f}% (7d)"
    draw.text((PAD + 280, py + 54), c7d_str, fill=c7d_color, font=_font(20, bold=True))

    # Stats grid
    stats = [
        ("Market Cap",         _fmt_big(mcap)),
        ("24h Volume",         _fmt_big(vol)),
        (f"Circulating Supply", f"{supply:,.0f} {symbol}"),
        ("All-Time High",      _fmt_price(ath)),
        ("All-Time Low",       _fmt_price(atl)),
    ]
    sy = HEADER_H + 110
    card_w = (IMG_W - PAD * 2 - 12) // 2
    for idx, (label, value) in enumerate(stats):
        col = idx % 2
        row = idx // 2
        cx = PAD + col * (card_w + 12)
        cy = sy + row * 90
        draw.rounded_rectangle([cx, cy, cx + card_w, cy + 76], radius=10, fill=C_CARD)
        draw.text((cx + 14, cy + 10), label, fill=C_MUTED, font=_font(14))
        draw.text((cx + 14, cy + 34), value, fill=C_TEXT, font=_font(20, bold=True))

    _draw_footer(draw, img_h)
    return _to_bytes(img)


# ── News card (fallback when no image_url) ────────────────────────────────────

def generate_news_card(article: dict) -> io.BytesIO:
    title   = article.get("title", "Crypto News")
    summary = article.get("summary", "")
    source  = article.get("source", "")

    HEADER_H = 70
    FOOTER_H = 40
    img_h = HEADER_H + 300 + FOOTER_H

    img = Image.new("RGB", (IMG_W, img_h), C_BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, IMG_W, HEADER_H], fill=C_HEADER)
    draw.rectangle([0, HEADER_H - 2, IMG_W, HEADER_H], fill=C_BORDER)
    draw.text((PAD, 16), "CRYPTO NEWS", fill=C_ACCENT, font=_font(22, bold=True))
    if source:
        draw.text((PAD, 46), source, fill=C_MUTED, font=_font(13))
    brand = config.PROMO_TERMINAL_NAME
    bw = _text_w(draw, brand, _font(14, bold=True))
    draw.text((IMG_W - PAD - bw, 26), brand, fill=C_GOLD, font=_font(14, bold=True))

    # Title (wrapped)
    y = HEADER_H + 20
    title_lines = textwrap.wrap(title, width=52)[:3]
    for line in title_lines:
        draw.text((PAD, y), line, fill=C_TEXT, font=_font(22, bold=True))
        y += 32

    # Divider
    y += 10
    draw.line([PAD, y, IMG_W - PAD, y], fill=C_BORDER, width=1)
    y += 16

    # Summary
    if summary:
        summary_lines = textwrap.wrap(summary[:300], width=72)[:5]
        for line in summary_lines:
            draw.text((PAD, y), line, fill=C_MUTED, font=_font(16))
            y += 24

    _draw_footer(draw, img_h, source=source or "RSS")
    return _to_bytes(img)


# ── Promo image: FUNDARBAS screenshot + branded footer ────────────────────────

def get_promo_image() -> io.BytesIO | None:
    """
    Loads a random FUNDARBAS screenshot from promo_images/ folder,
    adds a branded footer, and returns as BytesIO.
    Returns None if folder is empty.
    """
    if not os.path.isdir(PROMO_IMAGES_DIR):
        return None

    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    images = [
        f for f in os.listdir(PROMO_IMAGES_DIR)
        if os.path.splitext(f)[1].lower() in exts
    ]
    if not images:
        return None

    path = os.path.join(PROMO_IMAGES_DIR, random.choice(images))
    try:
        src = Image.open(path).convert("RGB")

        # Resize to IMG_W preserving aspect ratio
        if src.width != IMG_W:
            ratio = IMG_W / src.width
            new_h = int(src.height * ratio)
            src = src.resize((IMG_W, new_h), Image.LANCZOS)

        # Cap height at 600px
        if src.height > 600:
            src = src.crop((0, 0, IMG_W, 600))

        # Branded footer overlay
        footer_h = 54
        canvas = Image.new("RGB", (IMG_W, src.height + footer_h), C_HEADER)
        canvas.paste(src, (0, 0))

        draw = ImageDraw.Draw(canvas)
        fy = src.height
        draw.rectangle([0, fy, IMG_W, fy + footer_h], fill=C_HEADER)
        draw.rectangle([0, fy, IMG_W, fy + 2], fill=C_GOLD)

        name_text = config.PROMO_TERMINAL_NAME
        nw = _text_w(draw, name_text, _font(22, bold=True))
        draw.text(((IMG_W - nw) // 2, fy + 14), name_text, fill=C_GOLD, font=_font(22, bold=True))

        buf = io.BytesIO()
        canvas.save(buf, format="JPEG", quality=92)
        buf.seek(0)
        buf.name = "promo.jpg"
        return buf
    except Exception as e:
        logger.error(f"Failed to load promo image {path}: {e}")
        return None


def generate_security_image(article: dict) -> io.BytesIO:
    """Generates a dark red-toned security alert card for CertiK/SlowMist posts."""
    C_SEC_BG     = (12, 10, 16)
    C_SEC_HEADER = (22, 10, 28)
    C_SEC_ACCENT = (220, 50, 80)    # red accent
    C_SEC_GOLD   = (255, 196, 0)

    img_h = 420
    img = Image.new("RGB", (IMG_W, img_h), C_SEC_BG)
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([0, 0, IMG_W, 6], fill=C_SEC_ACCENT)
    draw.rectangle([0, 0, IMG_W, 64], fill=C_SEC_HEADER)
    draw.rectangle([0, 0, IMG_W, 6], fill=C_SEC_ACCENT)

    # Header row: shield icon + label
    source = article.get("source", "CertiK Skynet")
    header_text = f"🔐  БЕЗОПАСНОСТЬ  ·  {source.upper()}"
    hw = _text_w(draw, header_text, _font(17, bold=True))
    draw.text(((IMG_W - hw) // 2, 20), header_text, fill=C_SEC_ACCENT, font=_font(17, bold=True))

    # Title
    title = article.get("title", "")
    title_lines = textwrap.wrap(title, width=46)
    ty = 82
    for line in title_lines[:3]:
        draw.text((PAD, ty), line, fill=C_TEXT, font=_font(22, bold=True))
        ty += 34

    # Divider
    draw.line([PAD, ty + 8, IMG_W - PAD, ty + 8], fill=C_SEC_ACCENT, width=1)
    ty += 22

    # Summary
    summary = article.get("summary", "")
    if summary:
        summary_lines = textwrap.wrap(summary[:280], width=60)
        for line in summary_lines[:5]:
            draw.text((PAD, ty), line, fill=C_MUTED, font=_font(17))
            ty += 26

    # Footer
    draw.rectangle([0, img_h - 44, IMG_W, img_h], fill=C_SEC_HEADER)
    draw.rectangle([0, img_h - 44, IMG_W, img_h - 42], fill=C_SEC_ACCENT)
    ts = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    footer = f"skynet.certik.com  ·  {config.PROMO_TERMINAL_NAME}  ·  {ts}"
    fw = _text_w(draw, footer, _font(14))
    draw.text(((IMG_W - fw) // 2, img_h - 28), footer, fill=C_MUTED, font=_font(14))

    # Resize to content
    final_h = max(ty + 60, 280)
    final_h = min(final_h, img_h)
    img = img.crop((0, 0, IMG_W, final_h))

    return _to_bytes(img)


def generate_security_leaderboard_image(projects: list[dict]) -> io.BytesIO:
    """Generates a security leaderboard card showing top projects by CertiK score."""
    C_SEC_ACCENT = (220, 50, 80)
    row_h = 36
    header_h = 70
    footer_h = 44
    img_h = header_h + row_h * len(projects) + footer_h + 20

    img = Image.new("RGB", (IMG_W, img_h), (12, 10, 16))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, IMG_W, header_h], fill=(22, 10, 28))
    draw.rectangle([0, 0, IMG_W, 6], fill=C_SEC_ACCENT)

    header_text = "🔐  CERTIK SKYNET  ·  ТОП БЕЗОПАСНЫХ ПРОЕКТОВ"
    hw = _text_w(draw, header_text, _font(17, bold=True))
    draw.text(((IMG_W - hw) // 2, 20), header_text, fill=C_SEC_ACCENT, font=_font(17, bold=True))

    sub = "Рейтинг безопасности  ·  CertiK Security Leaderboard"
    sw = _text_w(draw, sub, _font(14))
    draw.text(((IMG_W - sw) // 2, 44), sub, fill=C_MUTED, font=_font(14))

    for i, proj in enumerate(projects):
        y = header_h + i * row_h + 10
        bg = (20, 26, 36) if i % 2 == 0 else (16, 21, 30)
        draw.rectangle([PAD, y, IMG_W - PAD, y + row_h - 4], fill=bg)

        rank_text = f"#{i + 1}"
        draw.text((PAD + 8, y + 8), rank_text, fill=C_MUTED, font=_font(16, bold=True))

        name = proj.get("name", "Unknown")[:28]
        draw.text((PAD + 52, y + 8), name, fill=C_TEXT, font=_font(17, bold=True))

        score = proj.get("score", 0)
        score_color = C_GREEN if score >= 80 else (C_GOLD if score >= 60 else C_RED)
        score_text = f"{score:.1f}" if isinstance(score, float) else str(score)
        sw2 = _text_w(draw, score_text, _font(17, bold=True))
        draw.text((IMG_W - PAD - sw2 - 8, y + 8), score_text, fill=score_color, font=_font(17, bold=True))

    fy = img_h - footer_h
    draw.rectangle([0, fy, IMG_W, img_h], fill=(22, 10, 28))
    draw.rectangle([0, fy, IMG_W, fy + 2], fill=C_SEC_ACCENT)
    ts = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    ft = f"skynet.certik.com  ·  {config.PROMO_TERMINAL_NAME}  ·  {ts}"
    ftw = _text_w(draw, ft, _font(13))
    draw.text(((IMG_W - ftw) // 2, fy + 14), ft, fill=C_MUTED, font=_font(13))

    return _to_bytes(img)


def generate_fact_image(fact: dict) -> io.BytesIO:
    """Generates a dark-themed card for an interesting crypto fact."""
    img_h = 420
    img = Image.new("RGB", (IMG_W, img_h), C_BG)
    draw = ImageDraw.Draw(img)

    # Gradient-style top bar with accent colour
    draw.rectangle([0, 0, IMG_W, 6], fill=C_ACCENT)

    # Header
    header_h = 64
    draw.rectangle([0, 0, IMG_W, header_h], fill=C_HEADER)
    draw.rectangle([0, 0, IMG_W, 6], fill=C_ACCENT)

    emoji = fact.get("emoji", "💡")
    category = fact.get("category", "").upper()
    header_text = f"{emoji}  КРИПТО-ФАКТ  ·  {category}"
    hw = _text_w(draw, header_text, _font(18, bold=True))
    draw.text(((IMG_W - hw) // 2, 20), header_text, fill=C_ACCENT, font=_font(18, bold=True))

    # Fact text — wrapped
    text = fact.get("text", "")
    wrapped = textwrap.wrap(text, width=52)
    ty = header_h + 30
    for line in wrapped:
        draw.text((PAD + 10, ty), line, fill=C_TEXT, font=_font(20))
        ty += 34

    # Divider
    draw.line([PAD, ty + 16, IMG_W - PAD, ty + 16], fill=C_BORDER, width=1)

    # Footer
    ts = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    footer = f"{config.PROMO_TERMINAL_NAME}  ·  {ts}"
    fw = _text_w(draw, footer, _font(15))
    draw.text(((IMG_W - fw) // 2, ty + 28), footer, fill=C_MUTED, font=_font(15))

    # Resize canvas to actual content height
    final_h = max(ty + 70, 280)
    img = img.crop((0, 0, IMG_W, final_h))

    return _to_bytes(img)


def generate_funding_image(rates: list[dict]) -> io.BytesIO:
    """Generates a dark-themed funding rate table for top perpetuals."""
    HEADER_H = 82
    FOOTER_H = 40
    COL_H_ROW = 30
    ROW_H = 52
    n = len(rates)
    img_h = HEADER_H + COL_H_ROW + n * ROW_H + FOOTER_H + 10

    img = Image.new("RGB", (IMG_W, img_h), C_BG)
    draw = ImageDraw.Draw(img)

    ts = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M UTC")
    _draw_header(draw, "FUNDING RATES  ·  ПЕРП. ФЬЮЧЕРСЫ", ts, HEADER_H)

    # Legend bar
    legend_y = HEADER_H + 4
    legend_items = [
        ("🔴 >0.1%", (255, 69, 58)), ("🟠 >0.03%", (255, 149, 0)),
        ("🟡 >0%", (255, 214, 10)), ("🟢 <0%", (52, 199, 89)),
        ("🔵 <-0.03%", (100, 180, 255)),
    ]
    lx = PAD
    for label, color in legend_items:
        draw.text((lx, legend_y), label, fill=color, font=_font(12))
        lx += _text_w(draw, label, _font(12)) + 18

    # Column headers
    cy = HEADER_H + COL_H_ROW + 4
    col_labels = [
        ("Монета",   PAD),
        ("Цена",     PAD + 120),
        ("8ч ставка", PAD + 280),
        ("Годовых",  PAD + 440),
        ("Сл. выплата", PAD + 580),
    ]
    for label, x in col_labels:
        draw.text((x, cy - 22), label, fill=C_MUTED, font=_font(13))
    draw.line([PAD, cy - 4, IMG_W - PAD, cy - 4], fill=C_BORDER, width=1)

    for i, row in enumerate(rates):
        ry = cy + i * ROW_H
        bg = C_CARD if i % 2 == 0 else C_CARD2
        draw.rectangle([0, ry - 2, IMG_W, ry + ROW_H - 4], fill=bg)

        rate_pct = row.get("rate_pct", 0)
        ann_pct = row.get("annualized_pct", 0)
        symbol = row.get("symbol", "")
        mark_price = row.get("mark_price", 0)
        next_ft = row.get("next_funding_time")

        if rate_pct > 0.1:
            rate_color = C_RED
        elif rate_pct > 0.03:
            rate_color = (255, 149, 0)
        elif rate_pct > 0:
            rate_color = C_GOLD
        elif rate_pct > -0.03:
            rate_color = C_GREEN
        else:
            rate_color = C_ACCENT

        prefix = "+" if rate_pct >= 0 else ""
        ann_prefix = "+" if ann_pct >= 0 else ""

        mid = ry + (ROW_H - 4) // 2 - 10

        draw.text((PAD, mid + 3), symbol, fill=C_TEXT, font=_font(18, bold=True))
        draw.text((PAD + 120, mid + 3), _fmt_price(mark_price), fill=C_TEXT, font=_font(15))
        draw.text((PAD + 280, mid + 3), f"{prefix}{rate_pct:.4f}%", fill=rate_color, font=_font(17, bold=True))
        draw.text((PAD + 440, mid + 3), f"{ann_prefix}{ann_pct:.1f}%", fill=rate_color, font=_font(15))

        if next_ft:
            next_str = next_ft.strftime("%H:%M UTC")
            draw.text((PAD + 580, mid + 3), next_str, fill=C_MUTED, font=_font(14))

    _draw_footer(draw, img_h, source="Binance Futures")
    return _to_bytes(img)


def generate_promo_card() -> io.BytesIO:
    """Generates a fallback promo card when no screenshots are available."""
    img_h = 400
    img = Image.new("RGB", (IMG_W, img_h), C_HEADER)
    draw = ImageDraw.Draw(img)

    # Gold accent bar at top
    draw.rectangle([0, 0, IMG_W, 6], fill=C_GOLD)
    draw.rectangle([0, img_h - 6, IMG_W, img_h], fill=C_GOLD)

    # Center content
    name = config.PROMO_TERMINAL_NAME
    slogan = config.PROMO_SLOGAN
    link = config.PROMO_LINK

    nw = _text_w(draw, name, _font(42, bold=True))
    draw.text(((IMG_W - nw) // 2, 80), name, fill=C_GOLD, font=_font(42, bold=True))

    sw_lines = textwrap.wrap(slogan, width=50)
    sy = 160
    for line in sw_lines:
        lw = _text_w(draw, line, _font(22))
        draw.text(((IMG_W - lw) // 2, sy), line, fill=C_TEXT, font=_font(22))
        sy += 36

    draw.line([IMG_W // 4, sy + 20, IMG_W * 3 // 4, sy + 20], fill=C_BORDER, width=1)

    lw = _text_w(draw, link, _font(18))
    draw.text(((IMG_W - lw) // 2, sy + 36), link, fill=C_ACCENT, font=_font(18))

    return _to_bytes(img)
