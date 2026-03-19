"""Админ-панель: изменение цены за 1 день."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import get_price_per_day, set_price_per_day, get_plans

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
        [InlineKeyboardButton(text="💰 Изменить цену за 1 день", callback_data="admin:price")],
        [InlineKeyboardButton(text="◀️ Закрыть", callback_data="admin:close")],
    ])


@router.message(Command("admin"), AdminFilter())
async def cmd_admin(msg: Message):
    price = await get_price_per_day()
    plans = await get_plans()
    month_price = round(30 * price)
    text = (
        "⚙️ *Админ-панель*\n\n"
        f"Цена за 1 день: *{price:.2f} ₽*\n"
        f"(30 дней = {month_price} ₽)\n\n"
        "*Текущие тарифы:*\n"
    )
    for p in plans:
        text += f"• {p['title']} — {p['price']} ₽\n"
    await msg.answer(text, parse_mode="Markdown", reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin:price", AdminFilter())
async def admin_set_price(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_price_per_day)
    price = await get_price_per_day()
    month_price = round(30 * price)
    await cb.message.edit_text(
        f"💰 *Изменение цены*\n\n"
        f"Сейчас: {price:.2f} ₽/день (месяц = {month_price} ₽)\n\n"
        "Введите новую цену за 1 день в рублях (например: 2.5 или 3):",
        parse_mode="Markdown",
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
        f"✅ Цена обновлена: *{price:.2f} ₽*/день\n"
        f"(30 дней = {month_price} ₽)\n\n"
        "*Тарифы:*\n"
    )
    for p in plans:
        text += f"• {p['title']} — {p['price']} ₽\n"
    await msg.answer(text, parse_mode="Markdown", reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin:close", AdminFilter())
async def admin_close(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.delete()
    await cb.answer()
