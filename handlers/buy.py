"""Покупка подписки за баланс."""

import time

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from database import get_or_create_user, get_plans, create_or_extend_subscription
from config import PUBLIC_BASE_URL
from handlers.cabinet import subscription_keyboard

router = Router()


async def _safe_edit_message(message: Message, text: str, reply_markup, parse_mode: str = "Markdown") -> None:
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
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)


async def plans_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    plans = await get_plans()
    rows = [
        [
            InlineKeyboardButton(
                text=f"{p['title']} — {p['price']} ₽",
                callback_data=f"buy:{p['id']}",
            )
        ]
        for p in plans
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "buy_sub")
async def buy_sub_start(cb: CallbackQuery):
    user = await get_or_create_user(cb.from_user.id)
    balance = user.get("balance") or 0
    plans = await get_plans()
    text = (
        "📦 *Купить подписку*\n\n"
        f"Ваш баланс: *{balance:.2f} ₽*\n\n"
        "Выберите тариф:"
    )
    for p in plans:
        text += f"\n• {p['title']} — {p['price']} ₽"
    await _safe_edit_message(
        cb.message,
        text,
        reply_markup=await plans_keyboard(),
        parse_mode="Markdown",
    )
    await cb.answer()


@router.callback_query(F.data == "plans")
async def show_plans(cb: CallbackQuery):
    plans = await get_plans()
    text = "📋 *Тарифы*\n\n"
    for p in plans:
        text += f"• *{p['title']}* — {p['price']} ₽ ({p['days']} дн.)\n"
    text += "\nНажмите «Купить подписку» для покупки."
    await _safe_edit_message(
        cb.message,
        text,
        reply_markup=await plans_keyboard(),
        parse_mode="Markdown",
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

    sub_url = (
        f"{PUBLIC_BASE_URL}/sub/{token}.txt"
        if PUBLIC_BASE_URL
        else "https://sub1.jetstoreapp.ru/v2raytun-sub"
    )

    expires_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(expires_at))
    kb = subscription_keyboard(sub_url)

    await _safe_edit_message(
        cb.message,
        f"✅ *Подписка активирована!*\n\n"
        f"Тариф: {plan['title']}\n"
        f"Действует до: {expires_str}\n\n"
        f"🔗 Ссылка подписки:\n`{sub_url}`\n\n"
        f"Нажмите кнопку ниже, чтобы открыть в приложении:",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await cb.answer("Подписка оформлена!")

