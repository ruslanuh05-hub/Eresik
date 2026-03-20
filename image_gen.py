"""Генерация изображения: наложение даты подписки на готовое фото."""
import io
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import (
    CABINET_BG_IMAGE,
    CABINET_TEXT_X,
    CABINET_TEXT_Y_FROM_BOTTOM,
    CABINET_LABEL_OFFSET,
    CABINET_DATE_OFFSET,
)


def generate_subscription_image(expires_at: int | None, nickname: str = "") -> bytes:
    """
    Накладывает дату подписки на фоновое изображение.
    Если подписки нет — пишет «Подписка не куплена».
    Возвращает bytes (PNG).
    """
    # Загружаем готовое фото или создаём fallback
    if CABINET_BG_IMAGE.exists():
        img = Image.open(CABINET_BG_IMAGE).convert("RGB")
    else:
        img = Image.new("RGB", (400, 200), color=(30, 35, 45))

    width, height = img.size
    draw = ImageDraw.Draw(img)

    # Шрифты
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except OSError:
        font_large = font_small = ImageFont.load_default()

    # Позиция текста (настраивается в config)
    if 0 <= CABINET_TEXT_X <= 1:
        cx = int(width * CABINET_TEXT_X)
    else:
        cx = int(CABINET_TEXT_X)
    text_y = height - CABINET_TEXT_Y_FROM_BOTTOM

    if expires_at and expires_at > int(time.time()):
        date_str = time.strftime("%d.%m.%Y", time.localtime(expires_at))
        time_str = time.strftime("%H:%M", time.localtime(expires_at))
        draw.text((cx, text_y + CABINET_LABEL_OFFSET), "Подписка до:", fill=(255, 255, 255), font=font_small, anchor="mm")
        _draw_text_with_outline(draw, (cx, text_y + CABINET_DATE_OFFSET), f"{date_str}  {time_str}", font_large, (80, 255, 120))
    else:
        draw.text((cx, text_y + (CABINET_LABEL_OFFSET + CABINET_DATE_OFFSET) // 2), "Подписка не куплена", fill=(255, 100, 100), font=font_large, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _draw_text_with_outline(draw, xy, text, font, fill, outline=(0, 0, 0), width=2):
    """Рисует текст с обводкой для читаемости на любом фоне."""
    x, y = xy
    for dx in (-width, 0, width):
        for dy in (-width, 0, width):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, fill=outline, font=font, anchor="mm")
    draw.text(xy, text, fill=fill, font=font, anchor="mm")
