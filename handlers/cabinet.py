"""Личный кабинет пользователя."""
import time as time_module
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from database import get_or_create_user

router = Router()


def _format_expires(ts: int | None) -> str:
    if not ts:
        return "—"
    remain = ts - int(time_module.time())
    if remain <= 0:
        return "Истекла"
    days = remain // 86400
    hours = (remain % 86400) // 3600
    if days > 0:
        return f"{days} дн. {hours} ч."
    return f"{hours} ч."


def _format_date(ts: int | None) -> str:
    if not ts:
        return "—"
    return time_module.strftime("%d.%m.%Y %H:%M", time_module.localtime(ts))


def main_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
    ])


async def build_cabinet_text(telegram_id: int) -> str:
    from config import PUBLIC_BASE_URL

    user = await get_or_create_user(telegram_id)
    balance = user.get("balance") or 0
    expires_at = user.get("subscription_expires_at")
    token = user.get("subscription_token")
    nickname = user.get("nickname") or user.get("username") or f"user_{telegram_id}"

    text = (
        "👤 *Личный кабинет*\n\n"
        f"🆔 Ник: `{nickname}`\n"
        f"💵 Баланс: *{balance:.2f} ₽*\n"
        f"📅 Подписка до: {_format_date(expires_at)}\n"
        f"⏱ Осталось: {_format_expires(expires_at)}\n"
    )
    if token and expires_at and expires_at > int(time_module.time()):
        sub_url = f"{PUBLIC_BASE_URL}/sub/{token}.txt" if PUBLIC_BASE_URL else "https://sub1.jetstoreapp.ru/v2raytun-sub"
        text += f"\n🔗 *Ссылка подписки:*\n`{sub_url}`"
    return text


@router.message(Command("my"))
@router.message(Command("cabinet"))
@router.message(Command("sub"))
async def cmd_my(msg: Message):
    text = await build_cabinet_text(msg.from_user.id)
    from handlers.start import main_keyboard
    await msg.answer(text, parse_mode="Markdown", reply_markup=main_keyboard())


@router.callback_query(F.data == "cabinet")
async def show_cabinet(cb: CallbackQuery):
    text = await build_cabinet_text(cb.from_user.id)
    from handlers.start import main_keyboard
    await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=main_keyboard())
    await cb.answer()
