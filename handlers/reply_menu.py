"""Нижняя reply-клавиатура главного экрана (без inline под приветствием)."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class ReplyMenu:
    SUBSCRIPTION = "Подписка"
    TOPUP = "Пополнить баланс"
    ABOUT = "О нас"
    PROFILE = "Профиль"
    SUPPORT = "Поддержка"


def reply_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ReplyMenu.SUBSCRIPTION)],
            [KeyboardButton(text=ReplyMenu.TOPUP)],
            [
                KeyboardButton(text=ReplyMenu.ABOUT),
                KeyboardButton(text=ReplyMenu.PROFILE),
                KeyboardButton(text=ReplyMenu.SUPPORT),
            ],
        ],
        resize_keyboard=True,
    )
