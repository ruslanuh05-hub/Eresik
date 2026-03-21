"""Покупка подписки за баланс."""

from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from database import get_or_create_user, get_plans, create_or_extend_subscription
from handlers.cabinet import build_purchase_success_text, device_selection_keyboard

router = Router()


async def _safe_edit_message(message: Message, text: str, reply_markup, parse_mode: str = "HTML") -> None:
    """
    Telegram: для сообщений с фото нужно редактировать caption, а не text.
    Делаем безопасный вариант с fallback на delete+answer.
    """
    try:
        if message.caption is not None:
            await message.edit_caption(text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception:
        # Сначала отправляем новый экран, потом удаляем старый.
        await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
        try:
            await message.delete()
        except Exception:
            pass


async def plans_keyboard(back_callback: str = "connect_menu"):
    """Назад — в подменю «Подключиться» (или переданный callback)."""
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
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.in_(("buy_sub", "buy_sub:subs")))
async def buy_sub_start(cb: CallbackQuery):
    user = await get_or_create_user(cb.from_user.id)
    balance = user.get("balance") or 0
    plans = await get_plans()
    # Из «Мои подписки» (нет активной подписки) — назад туда; из «Подключиться» — в connect_menu
    back_cb = "my_subscriptions" if cb.data == "buy_sub:subs" else "connect_menu"
    text = (
        "📦 <b>Купить подписку</b>\n\n"
        f"Ваш баланс: <b>{balance:.2f} ₽</b>\n\n"
        "Выберите тариф:"
    )
    for p in plans:
        text += f"\n• {escape(p['title'])} — {p['price']} ₽"
    await _safe_edit_message(
        cb.message,
        text,
        reply_markup=await plans_keyboard(back_callback=back_cb),
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

