"""Команды /start и главное меню."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from database import get_or_create_user

router = Router()


def main_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="cabinet")],
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="topup")],
        [InlineKeyboardButton(text="📦 Купить подписку", callback_data="buy_sub")],
        [InlineKeyboardButton(text="📋 Тарифы", callback_data="plans")],
    ])


@router.message(CommandStart())
async def cmd_start(msg: Message):
    user = await get_or_create_user(msg.from_user.id, msg.from_user.username)
    text = (
        "👋 Добро пожаловать в JetVPN!\n\n"
        "Здесь вы можете:\n"
        "• Пополнить баланс и купить подписку\n"
        "• Управлять своей подпиской\n"
        "• Получить ссылку на VPN для v2raytun\n\n"
        "Выберите действие:"
    )
    await msg.answer(text, reply_markup=main_keyboard())


@router.callback_query(F.data == "main_menu")
async def back_to_main(cb: CallbackQuery):
    await cb.message.edit_text(
        "Выберите действие:",
        reply_markup=main_keyboard(),
    )
    await cb.answer()
