"""Команды /start и главное меню."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart

from database import get_or_create_user
from config import WELCOME_IMAGE

router = Router()


def main_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="cabinet")],
        [InlineKeyboardButton(text="📱 Мои подписки", callback_data="my_subscriptions")],
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="topup")],
        [InlineKeyboardButton(text="📦 Купить подписку", callback_data="buy_sub")],
        [InlineKeyboardButton(text="📋 Тарифы", callback_data="plans")],
    ])


def _welcome_text() -> str:
    return (
        "👋 Добро пожаловать в JetVPN!\n\n"
        "Здесь вы можете:\n"
        "• Пополнить баланс и купить подписку\n"
        "• Управлять своей подпиской\n"
        "• Получить ссылку на VPN для v2raytun\n\n"
        "Выберите действие:"
    )


@router.message(CommandStart())
async def cmd_start(msg: Message):
    user = await get_or_create_user(msg.from_user.id, msg.from_user.username)
    text = _welcome_text()
    kb = main_keyboard()
    if WELCOME_IMAGE.exists():
        photo = FSInputFile(WELCOME_IMAGE)
        await msg.answer_photo(photo, caption=text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


@router.callback_query(F.data == "main_menu")
async def back_to_main(cb: CallbackQuery):
    text = "Выберите действие:"
    kb = main_keyboard()
    if WELCOME_IMAGE.exists():
        # Главное меню с фото — всегда удаляем текущее и отправляем фото
        await cb.message.delete()
        photo = FSInputFile(WELCOME_IMAGE)
        await cb.message.answer_photo(photo, caption=text, reply_markup=kb)
    else:
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except Exception:
            await cb.message.delete()
            await cb.message.answer(text, reply_markup=kb)
    await cb.answer()
