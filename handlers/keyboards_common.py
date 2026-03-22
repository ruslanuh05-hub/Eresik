"""Общие inline-кнопки: «Назад» с премиум-стрелкой (E.BACKARROW)."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgemoji import E


def back_btn(*, callback_data: str = "main_menu", text: str = "Назад") -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        icon_custom_emoji_id=E.BACKARROW,
    )


def row_back_main() -> list[InlineKeyboardButton]:
    return [back_btn(callback_data="main_menu", text="Назад")]


def markup_back_main_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[row_back_main()])
