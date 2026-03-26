"""Админ-панель: изменение цены за 1 день."""
from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import get_price_per_day, set_price_per_day, get_plans
from tgemoji import E

router = Router()


class AdminFilter(Filter):
    """Фильтр: только админы."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in ADMIN_IDS


class AdminStates(StatesGroup):
    waiting_price_per_day = State()


def admin_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Изменить цену за 1 день",
                callback_data="admin:price",
                icon_custom_emoji_id=E.MONEY,
            )
        ],
        [InlineKeyboardButton(text="◀️ Закрыть", callback_data="admin:close")],
    ])


@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Доступ запрещен.")
        return

    # `/admin` теперь открывает вашу расширенную админ-панель (а редактирование цены доступно в разделе "Настройки").
    from handlers.admin_panel import admin_main_keyboard

    await msg.answer("🔧 Админ-панель", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "admin:price", AdminFilter())
async def admin_set_price(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_price_per_day)
    price = await get_price_per_day()
    month_price = round(30 * price)
    await cb.message.edit_text(
        f"💰 <b>Изменение цены</b>\n\n"
        f"Сейчас: {price:.2f} ₽/день (месяц = {month_price} ₽)\n\n"
        "Введите новую цену за 1 день в рублях (например: 2.5 или 3):",
        parse_mode="HTML",
    )
    await cb.answer()


@router.message(AdminStates.waiting_price_per_day, F.text, AdminFilter())
async def admin_price_received(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.replace(",", ".").replace(" ", ""))
    except ValueError:
        await msg.answer("Введите число, например: 2.5")
        return

    if price <= 0 or price > 1000:
        await msg.answer("Цена должна быть от 0.01 до 1000 ₽")
        return

    try:
        await set_price_per_day(price)
    except ValueError as e:
        await msg.answer(str(e))
        return

    await state.clear()
    plans = await get_plans()
    month_price = round(30 * price)
    text = (
        f"✅ Цена обновлена: <b>{price:.2f} ₽</b>/день\n"
        f"(30 дней = {month_price} ₽)\n\n"
        "<b>Тарифы:</b>\n"
    )
    for p in plans:
        text += f"• {escape(p['title'])} — {p['price']} ₽\n"
    await msg.answer(text, parse_mode="HTML", reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin:close", AdminFilter())
async def admin_close(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.delete()
    await cb.answer()
