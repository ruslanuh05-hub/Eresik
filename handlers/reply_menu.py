"""Нижняя reply-клавиатура главного экрана.

Премиум-иконка на кнопке (как у других ботов) — через Bot API:
  KeyboardButton(text="Подписка", icon_custom_emoji_id="…")
Тот же механизм, что у InlineKeyboardButton: ID из набора Fragment / доступного боту.

Условия Telegram: бот с именем с Fragment или владелец с Premium — см. справку API.
В text только подпись (без копипаста премиум-символа из чата).
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from tgemoji import E


class ReplyMenu:
    """Текст кнопки = то, что приходит в чат при нажатии (фильтры F.text)."""

    SUBSCRIPTION = "Подписка"
    TOPUP = "Пополнить баланс"
    ABOUT = "О нас"
    HELP = "Помощь"
    PROFILE = "Профиль"


def reply_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=ReplyMenu.SUBSCRIPTION,
                    icon_custom_emoji_id=E.MOLNY,
                ),
            ],
            [
                KeyboardButton(
                    text=ReplyMenu.TOPUP,
                    icon_custom_emoji_id=E.MONEY,
                ),
            ],
            [
                KeyboardButton(
                    text=ReplyMenu.ABOUT,
                    icon_custom_emoji_id=E.FORME,
                ),
                KeyboardButton(
                    text=ReplyMenu.HELP,
                    icon_custom_emoji_id=E.HELP,
                ),
                KeyboardButton(
                    text=ReplyMenu.PROFILE,
                    icon_custom_emoji_id=E.PROF,
                ),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="👇 Выберите действие",
    )
