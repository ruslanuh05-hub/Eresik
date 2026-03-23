"""Покупка подписки за баланс."""

from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from database import get_or_create_user, get_plans, create_or_extend_subscription
from handlers.cabinet import build_purchase_success_text, device_selection_keyboard
from handlers.keyboards_common import back_btn
from handlers.ui_nav import apply_screen_from_message

router = Router()


async def _safe_edit_message(message: Message, text: str, reply_markup, parse_mode: str = "HTML") -> None:
    """Сообщение с фото — возвращаем приветственный кадр + подпись."""
    await apply_screen_from_message(
        message,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        photo_mode="welcome",
    )


async def plans_keyboard(back_callback: str = "connect_menu"):
    """Тарифы + «Назад» с настраиваемым callback."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    plans = await get_plans()
    rows = [
        [
            InlineKeyboardButton(
                text=f"{escape(p['title'])} — {p['price']} ₽",
                callback_data=f"buy:{p['id']}",
            )
        ]
        for p in plans
    ]
    rows.append([back_btn(callback_data=back_callback, text="Назад")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.in_(("buy_sub", "buy_sub:subs")))
async def buy_sub_start(cb: CallbackQuery):
    user = await get_or_create_user(cb.from_user.id)
    balance = user.get("balance") or 0
    plans = await get_plans()
    text = (
        "📦 <b>Купить подписку</b>\n\n"
        f"Ваш баланс: <b>{balance:.2f} ₽</b>\n\n"
        "Выберите тариф:"
    )
    for p in plans:
        text += f"\n• {escape(p['title'])} — {p['price']} ₽"
    back_callback = "my_subscriptions" if cb.data == "buy_sub:subs" else "connect_menu"
    await _safe_edit_message(
        cb.message,
        text,
        reply_markup=await plans_keyboard(back_callback=back_callback),
        parse_mode="HTML",
    )
    await cb.answer()


@router.callback_query(F.data == "plans")
async def show_plans(cb: CallbackQuery):
    plans = await get_plans()
    text = "📋 <b>Тарифы</b>\n\n"
    for p in plans:
        text += f"• <b>{escape(p['title'])}</b> — {p['price']} ₽ ({p['days']} дн.)\n"
    text += "\nНажмите «Купить подписку» для покупки."
    await _safe_edit_message(
        cb.message,
        text,
        reply_markup=await plans_keyboard(),
        parse_mode="HTML",
    )
    await cb.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy_plan(cb: CallbackQuery):
    plan_id = cb.data.split(":")[1]
    plans = {p["id"]: p for p in await get_plans()}
    plan = plans.get(plan_id)
    if not plan:
        await cb.answer("Тариф не найден", show_alert=True)
        return

    try:
        token, expires_at = await create_or_extend_subscription(
            cb.from_user.id,
            plan["days"],
            plan_id,
            plan["price"],
        )
    except ValueError as e:
        await cb.answer(str(e), show_alert=True)
        return

    success_text = build_purchase_success_text(plan["title"], expires_at)
    await _safe_edit_message(
        cb.message,
        success_text,
        reply_markup=device_selection_keyboard(),
        parse_mode="HTML",
    )
    await cb.answer("Подписка оформлена!")

