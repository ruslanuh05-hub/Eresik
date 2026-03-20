"""Пополнение баланса через FreeKassa."""

import time

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_or_create_user, add_payment, add_balance
from freekassa import create_payment_url
from config import FREKASSA_SHOP_ID, PUBLIC_BASE_URL, ADMIN_IDS

router = Router()


class TopUpStates(StatesGroup):
    waiting_amount = State()


def topup_keyboard(is_admin: bool = False):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    amounts = [(99, "99 ₽"), (199, "199 ₽"), (499, "499 ₽"), (999, "999 ₽")]
    rows = [
        [
            InlineKeyboardButton(text=f"{amt} ₽", callback_data=f"topup:{amt}")
            for amt, _ in [amounts[0], amounts[1]]
        ],
        [
            InlineKeyboardButton(text=f"{amt} ₽", callback_data=f"topup:{amt}")
            for amt, _ in [amounts[2], amounts[3]]
        ],
        [InlineKeyboardButton(text="✏️ Своя сумма", callback_data="topup:custom")],
    ]

    if is_admin:
        rows.append([InlineKeyboardButton(text="🧪 Тестовая оплата 100 ₽", callback_data="topup:test:100")])

    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "topup")
async def topup_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(cb.from_user.id)
    balance = user.get("balance") or 0
    is_admin = cb.from_user.id in ADMIN_IDS

    text = (
        f"💳 *Пополнение баланса*\n\n"
        f"Текущий баланс: *{balance:.2f} ₽*\n\n"
        "Выберите сумму или введите свою (минимум 50 ₽):"
    )
    try:
        await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=topup_keyboard(is_admin))
    except Exception:
        await cb.message.delete()
        await cb.message.answer(text, parse_mode="Markdown", reply_markup=topup_keyboard(is_admin))
    await cb.answer()


@router.callback_query(F.data.startswith("topup:"))
async def topup_amount(cb: CallbackQuery, state: FSMContext):
    data = cb.data.split(":")

    if data[1] == "custom":
        await state.set_state(TopUpStates.waiting_amount)
        await cb.message.edit_text(
            "✏️ Введите сумму пополнения (минимум 50 ₽):",
            reply_markup=None,
        )
        await cb.answer()
        return

    # Тестовая оплата (только для админов)
    if data[1] == "test":
        if cb.from_user.id not in ADMIN_IDS:
            await cb.answer("Доступ запрещён", show_alert=True)
            return
        try:
            amount = float(data[2]) if len(data) > 2 else 100.0
        except (ValueError, IndexError):
            amount = 100.0
        await process_test_payment(cb, cb.from_user.id, amount)
        await cb.answer()
        return

    try:
        amount = float(data[1])
    except (ValueError, IndexError):
        await cb.answer("Неверная сумма", show_alert=True)
        return

    if amount < 50:
        await cb.answer("Минимум 50 ₽", show_alert=True)
        return

    await process_topup(cb, cb.from_user.id, amount)
    await cb.answer()


@router.message(TopUpStates.waiting_amount, F.text)
async def topup_custom_amount(msg: Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(",", ".").replace(" ", ""))
    except ValueError:
        await msg.answer("Введите число, например: 150")
        return

    if amount < 50:
        await msg.answer("Минимальная сумма — 50 ₽")
        return

    await state.clear()
    await do_send_payment_link(msg, msg.from_user.id, amount)


async def process_test_payment(cb: CallbackQuery, telegram_id: int, amount: float):
    """Симуляция успешной оплаты (только для админов)."""
    order_id = f"test_jvpn_{telegram_id}_{int(time.time())}"
    await add_payment(telegram_id, amount, order_id, order_id, "completed")
    new_balance = await add_balance(telegram_id, amount)
    await cb.message.edit_text(
        f"🧪 *Тестовая оплата выполнена*\n\n"
        f"Зачислено: *{amount:.2f} ₽*\n"
        f"Новый баланс: *{new_balance:.2f} ₽*",
        parse_mode="Markdown",
        reply_markup=topup_keyboard(is_admin=True),
    )


async def process_topup(cb: CallbackQuery, telegram_id: int, amount: float):
    """Создать платёж и отправить ссылку (для callback из кнопок)."""
    if not FREKASSA_SHOP_ID or not PUBLIC_BASE_URL:
        await cb.message.edit_text(
            "⚠️ Оплата через FreeKassa не настроена. Обратитесь к администратору.",
            reply_markup=None,
        )
        return

    order_id = f"jvpn_{telegram_id}_{int(time.time())}"
    url = create_payment_url(amount, order_id, telegram_id)
    if not url:
        await cb.message.edit_text("⚠️ Ошибка создания платежа.", reply_markup=None)
        return

    await add_payment(telegram_id, amount, order_id, "", "pending")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Перейти к оплате", url=url)],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="topup")],
        ]
    )
    await cb.message.edit_text(
        f"💳 *Оплата {amount:.2f} ₽*\n\n"
        "Нажмите кнопку ниже для перехода к оплате.\n"
        "После успешной оплаты баланс пополнится автоматически.",
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def do_send_payment_link(msg: Message, telegram_id: int, amount: float):
    """Отправить ссылку на оплату (для custom amount)."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    if not FREKASSA_SHOP_ID or not PUBLIC_BASE_URL:
        await msg.answer("⚠️ Оплата не настроена.")
        return

    order_id = f"jvpn_{telegram_id}_{int(time.time())}"
    url = create_payment_url(amount, order_id, telegram_id)
    if not url:
        await msg.answer("⚠️ Ошибка создания платежа.")
        return

    await add_payment(telegram_id, amount, order_id, "", "pending")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Перейти к оплате", url=url)],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="topup")],
        ]
    )
    await msg.answer(
        f"💳 *Оплата {amount:.2f} ₽*\n\n"
        "Нажмите кнопку ниже для перехода к оплате.",
        parse_mode="Markdown",
        reply_markup=kb,
    )

