"""Плавная смена экрана: меняем media/клавиатуру так, чтобы профиль не «залипал»."""

import io
import logging
from typing import Literal

from PIL import Image

from aiogram.types import (
    CallbackQuery,
    Message,
    FSInputFile,
    BufferedInputFile,
    InputMediaPhoto,
)

from config import (
    WELCOME_IMAGE,
    CABINET_BG_IMAGE,
    ABOUT_IMAGE,
    SUPPORT_IMAGE,
    CONNECT_IMAGE,
    TOPUP_IMAGE,
    SUBSCRIPTIONS_IMAGE,
    BUY_SUBSCRIPTION_IMAGE,
)

logger = logging.getLogger("jvpn-bot.ui_nav")

_PLACEHOLDER_CACHE: dict[str, bytes] = {}


def _placeholder_png_bytes(color: tuple[int, int, int]) -> bytes:
    key = f"{color[0]}_{color[1]}_{color[2]}"
    if key in _PLACEHOLDER_CACHE:
        return _PLACEHOLDER_CACHE[key]
    # Без текста на картинке: только фон для корректной смены media.
    img = Image.new("RGB", (400, 200), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    _PLACEHOLDER_CACHE[key] = buf.getvalue()
    return _PLACEHOLDER_CACHE[key]


def _photo_path_for_mode(photo_mode: str):
    # alias: "welcome" => главное меню
    if photo_mode == "welcome":
        return WELCOME_IMAGE
    if photo_mode == "cabinet":
        return CABINET_BG_IMAGE
    if photo_mode == "about":
        return ABOUT_IMAGE
    if photo_mode == "support":
        return SUPPORT_IMAGE
    if photo_mode == "connect":
        return CONNECT_IMAGE
    if photo_mode == "subs":
        return SUBSCRIPTIONS_IMAGE
    if photo_mode == "buy":
        return BUY_SUBSCRIPTION_IMAGE
    if photo_mode == "topup":
        return TOPUP_IMAGE
    return None


def _placeholder_color_for_mode(photo_mode: str) -> tuple[int, int, int]:
    return {
        "welcome": (10, 30, 60),
        "cabinet": (30, 30, 30),
        "about": (60, 30, 10),
        "support": (10, 60, 30),
        "connect": (60, 60, 10),
        "subs": (60, 60, 10),
        "buy": (60, 60, 10),
        "topup": (20, 60, 70),
    }.get(photo_mode, (10, 30, 60))


async def apply_screen_from_callback(
    cb: CallbackQuery,
    *,
    text: str,
    reply_markup,
    parse_mode: str | None = "HTML",
    photo_mode: Literal["welcome", "cabinet", "about", "support", "connect", "subs", "buy", "topup", "none"] = "welcome",
) -> None:
    """
    Обновить сообщение с callback: при наличии фото — заменить медиа + подпись (главное меню / профиль).
    Иначе — caption/text/answer.
    """
    msg = cb.message
    if not msg:
        return

    if photo_mode != "none" and msg.photo:
        photo_path = _photo_path_for_mode(photo_mode)
        try:
            if photo_path is not None and photo_path.exists():
                media_obj = FSInputFile(photo_path)
            else:
                # jpg может отсутствовать: подставим placeholder, чтобы edit_media всегда работал.
                color = _placeholder_color_for_mode(photo_mode)
                placeholder = _placeholder_png_bytes(color)
                media_obj = BufferedInputFile(placeholder, filename=f"{photo_mode}.png")

            await msg.edit_media(
                InputMediaPhoto(
                    media=media_obj,
                    caption=text,
                    parse_mode=parse_mode,
                ),
                reply_markup=reply_markup,
            )
            return
        except Exception:
            logger.debug("apply_screen: edit_media failed", exc_info=True)

    try:
        # Для сообщений с фото всегда редактируем caption (даже если caption сейчас None).
        if msg.photo:
            if parse_mode is not None:
                await msg.edit_caption(caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await msg.edit_caption(caption=text, reply_markup=reply_markup)
        else:
            if parse_mode is not None:
                await msg.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await msg.edit_text(text, reply_markup=reply_markup)
    except Exception:
        logger.debug("apply_screen: edit caption/text failed", exc_info=True)
        await msg.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)


async def apply_screen_from_message(
    message: Message,
    *,
    text: str,
    reply_markup,
    parse_mode: str | None = "HTML",
    photo_mode: Literal["welcome", "cabinet", "about", "support", "connect", "subs", "buy", "topup", "none"] = "welcome",
) -> None:
    """То же для Message (topup/buy без CallbackQuery в сигнатуре)."""
    if photo_mode != "none" and message.photo:
        photo_path = _photo_path_for_mode(photo_mode)
        try:
            if photo_path is not None and photo_path.exists():
                media_obj = FSInputFile(photo_path)
            else:
                color = _placeholder_color_for_mode(photo_mode)
                placeholder = _placeholder_png_bytes(color)
                media_obj = BufferedInputFile(placeholder, filename=f"{photo_mode}.png")

            await message.edit_media(
                InputMediaPhoto(
                    media=media_obj,
                    caption=text,
                    parse_mode=parse_mode,
                ),
                reply_markup=reply_markup,
            )
            return
        except Exception:
            logger.debug("apply_screen_from_message: edit_media failed", exc_info=True)

    try:
        if message.photo:
            if parse_mode is not None:
                await message.edit_caption(caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await message.edit_caption(caption=text, reply_markup=reply_markup)
        else:
            if parse_mode is not None:
                await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        logger.debug("apply_screen_from_message: edit failed", exc_info=True)
        await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
