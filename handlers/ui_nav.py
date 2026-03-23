"""Плавная смена экрана: edit_media, чтобы фото профиля не «залипало» на приветствии."""

import logging
from typing import Literal

from aiogram.types import (
    CallbackQuery,
    Message,
    FSInputFile,
    BufferedInputFile,
    InputMediaPhoto,
)

from config import WELCOME_IMAGE

logger = logging.getLogger("jvpn-bot.ui_nav")


async def apply_screen_from_callback(
    cb: CallbackQuery,
    *,
    text: str,
    reply_markup,
    parse_mode: str | None = "HTML",
    photo_mode: Literal["welcome", "cabinet", "none"] = "welcome",
    cabinet_png: bytes | None = None,
) -> None:
    """
    Обновить сообщение с callback: при наличии фото — заменить медиа + подпись (главное меню / профиль).
    Иначе — caption/text/answer.
    """
    msg = cb.message
    if not msg:
        return

    if photo_mode == "cabinet" and cabinet_png and msg.photo:
        try:
            await msg.edit_media(
                InputMediaPhoto(
                    media=BufferedInputFile(cabinet_png, filename="cabinet.png"),
                    caption=text,
                    parse_mode=parse_mode,
                ),
                reply_markup=reply_markup,
            )
            return
        except Exception:
            logger.debug("apply_screen: cabinet edit_media failed", exc_info=True)

    if photo_mode == "welcome" and WELCOME_IMAGE.exists() and msg.photo:
        try:
            await msg.edit_media(
                InputMediaPhoto(
                    media=FSInputFile(WELCOME_IMAGE),
                    caption=text,
                    parse_mode=parse_mode,
                ),
                reply_markup=reply_markup,
            )
            return
        except Exception:
            logger.debug("apply_screen: welcome edit_media failed", exc_info=True)

    try:
        if msg.caption is not None:
            await msg.edit_caption(caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            await msg.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception:
        logger.debug("apply_screen: edit caption/text failed", exc_info=True)
        await msg.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)


async def apply_screen_from_message(
    message: Message,
    *,
    text: str,
    reply_markup,
    parse_mode: str | None = "HTML",
    photo_mode: Literal["welcome", "cabinet", "none"] = "welcome",
    cabinet_png: bytes | None = None,
) -> None:
    """То же для Message (topup/buy без CallbackQuery в сигнатуре)."""
    if photo_mode == "cabinet" and cabinet_png and message.photo:
        try:
            await message.edit_media(
                InputMediaPhoto(
                    media=BufferedInputFile(cabinet_png, filename="cabinet.png"),
                    caption=text,
                    parse_mode=parse_mode,
                ),
                reply_markup=reply_markup,
            )
            return
        except Exception:
            logger.debug("apply_screen_from_message: cabinet edit_media failed", exc_info=True)

    if photo_mode == "welcome" and WELCOME_IMAGE.exists() and message.photo:
        try:
            await message.edit_media(
                InputMediaPhoto(
                    media=FSInputFile(WELCOME_IMAGE),
                    caption=text,
                    parse_mode=parse_mode,
                ),
                reply_markup=reply_markup,
            )
            return
        except Exception:
            logger.debug("apply_screen_from_message: welcome edit_media failed", exc_info=True)

    try:
        if message.caption is not None:
            await message.edit_caption(caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception:
        logger.debug("apply_screen_from_message: edit failed", exc_info=True)
        await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
