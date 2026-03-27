"""Покупка подписки за баланс."""

import time
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
        photo_mode="buy",
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


@router.callback_query(F.data.in_(("buy_sub", "buy_sub:subs", "renew_sub")))
async def buy_sub_start(cb: CallbackQuery):
    user = await get_or_create_user(cb.from_user.id)
    balance = user.get("balance") or 0
    plans = await get_plans()
    is_renew = cb.data == "renew_sub"
    title = "🔄 <b>Продлить подписку</b>" if is_renew else "📦 <b>Купить подписку</b>"
    text = f"{title}\n\n" f"Ваш баланс: <b>{balance:.2f} ₽</b>\n\n" "Выберите тариф:"
    for p in plans:
        text += f"\n• {escape(p['title'])} — {p['price']} ₽"
    if cb.data == "renew_sub":
        back_callback = "cabinet"
    elif cb.data == "buy_sub:subs":
        back_callback = "my_subscriptions"
    else:
        back_callback = "connect_menu"
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

    user_before = await get_or_create_user(cb.from_user.id)
    now = int(time.time())
    was_active = bool((user_before.get("subscription_expires_at") or 0) > now)

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

    # Экран после покупки: как "Мои подписки", но с текстом успеха.
    # Кнопки дальше приведут к шагу подключения (subdev:*).
    success_title = "✅ <b>Подписка продлена</b>" if was_active else "✅ <b>Успешная оплата</b>"
    success_text = (
        f"{success_title}\n\n"
        "Подключите подписку:\n"
    )
    await _safe_edit_message(
        cb.message,
        success_text,
        reply_markup=device_selection_keyboard(back_callback="buy_sub"),
        parse_mode="HTML",
    )
    await cb.answer()

