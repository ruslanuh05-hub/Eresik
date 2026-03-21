"""Личный кабинет пользователя."""

import time as time_module
from urllib.parse import quote

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    BufferedInputFile,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command

from database import get_or_create_user
from image_gen import generate_subscription_image
from config import IMPORT_BRIDGE_BASE, PUBLIC_BASE_URL, UPSTREAM_SUB_URL

router = Router()


async def _safe_edit_message(cb: CallbackQuery, text: str, reply_markup=None, parse_mode: str = "Markdown"):
    """Безопасно редактировать text/caption из callback."""
    try:
        if cb.message and cb.message.caption is not None:
            await cb.message.edit_caption(caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            await cb.message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception:
        await cb.message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
        try:
            await cb.message.delete()
        except Exception:
            pass


def device_selection_keyboard() -> InlineKeyboardMarkup:
    """Шаг 1: выбор устройства (Android | iOS / ПК)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 ANDROID", callback_data="subdev:android"),
                InlineKeyboardButton(text="🍏 iOS", callback_data="subdev:ios"),
            ],
            [InlineKeyboardButton(text="🖥 ПК", callback_data="subdev:pc")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
        ]
    )


def _bridge_url(app: str, personal_sub_url: str) -> str:
    base = (IMPORT_BRIDGE_BASE or "").rstrip("/")
    return f"{base}/open/{app}?u={quote(personal_sub_url, safe='')}"


def app_import_keyboard(platform: str, personal_sub_url: str) -> InlineKeyboardMarkup:
    """
    Шаг 2: кнопки-ссылки на HTTPS-страницу /open/... (редирект в приложение).
    Android / iOS: v2RayTun | Happ; ПК: Hiddify | Happ.
    """
    if not IMPORT_BRIDGE_BASE or not personal_sub_url:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К выбору устройства", callback_data="subdev:menu")],
                [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")],
            ]
        )

    rows = []
    if platform in ("android", "ios"):
        rows.append(
            [
                InlineKeyboardButton(text="📱 v2RayTun", url=_bridge_url("v2raytun", personal_sub_url)),
                InlineKeyboardButton(text="📱 Happ", url=_bridge_url("happ", personal_sub_url)),
            ]
        )
    elif platform == "pc":
        rows.append(
            [
                InlineKeyboardButton(text="📱 Hiddify", url=_bridge_url("hiddify", personal_sub_url)),
                InlineKeyboardButton(text="📱 Happ", url=_bridge_url("happ", personal_sub_url)),
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ К выбору устройства", callback_data="subdev:menu")])
    rows.append([InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cabinet_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура личного кабинета без кнопок приложений."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
        ]
    )


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


def _platform_title(platform: str) -> str:
    return {"android": "📱 Android", "ios": "🍏 iOS", "pc": "🖥 ПК"}.get(platform, platform)


def build_purchase_success_text(plan_title: str, personal_sub_url: str, expires_at: int) -> str:
    """Текст после успешной покупки: ссылка + выбор устройства."""
    return (
        "✅ *Подписка активирована!*\n\n"
        f"Тариф: {plan_title}\n\n"
        f"🔗 Ссылка подписки:\n`{personal_sub_url}`\n\n"
        f"📅 Действует до: {_format_date(expires_at)}\n"
        f"⏱ Осталось: {_format_expires(expires_at)}\n\n"
        "Выберите устройство:"
    )


def build_my_subscriptions_text(
    personal_sub_url: str,
    expires_at: int,
    platform: str | None = None,
) -> str:
    """Текст экрана «Мои подписки»."""
    base = (
        "📱 *Мои подписки*\n\n"
        f"🔗 Ссылка подписки:\n`{personal_sub_url}`\n\n"
        f"📅 Действует до: {_format_date(expires_at)}\n"
        f"⏱ Осталось: {_format_expires(expires_at)}\n\n"
    )
    if platform is None:
        return base + "Выберите устройство:"
    return (
        base
        + f"{_platform_title(platform)}\n\n"
        + "Выберите приложение — откроется страница импорта в браузере:"
    )


async def build_cabinet_text(telegram_id: int) -> str:
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
        personal_sub_url = (
            f"{PUBLIC_BASE_URL}/sub/{token}.txt" if PUBLIC_BASE_URL else f"{UPSTREAM_SUB_URL}?token={token}"
        )
        text += f"\n🔗 *Ссылка подписки:*\n`{personal_sub_url}`"

    return text


async def _sub_url_for_user(telegram_id: int) -> str | None:
    user = await get_or_create_user(telegram_id)
    token = user.get("subscription_token")
    expires_at = user.get("subscription_expires_at")
    if token and expires_at and expires_at > int(time_module.time()):
        if PUBLIC_BASE_URL:
            return f"{PUBLIC_BASE_URL}/sub/{token}.txt"
        return f"{UPSTREAM_SUB_URL}?token={token}"
    return None


@router.message(Command("my"))
@router.message(Command("cabinet"))
async def cmd_my(msg: Message):
    user = await get_or_create_user(msg.from_user.id)
    text = await build_cabinet_text(msg.from_user.id)

    kb = cabinet_keyboard()
    try:
        img_bytes = generate_subscription_image(
            user.get("subscription_expires_at"),
            user.get("nickname") or msg.from_user.username or "",
        )
        photo = BufferedInputFile(img_bytes, filename="cabinet.png")
        await msg.answer_photo(photo, caption=text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        await msg.answer(text, parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data == "cabinet")
async def show_cabinet(cb: CallbackQuery):
    user = await get_or_create_user(cb.from_user.id)
    text = await build_cabinet_text(cb.from_user.id)
    kb = cabinet_keyboard()
    try:
        img_bytes = generate_subscription_image(
            user.get("subscription_expires_at"),
            user.get("nickname") or cb.from_user.username or "",
        )
        photo = BufferedInputFile(img_bytes, filename="cabinet.png")
        try:
            media = InputMediaPhoto(media=photo, caption=text, parse_mode="Markdown")
            await cb.message.edit_media(media=media, reply_markup=kb)
        except Exception:
            await cb.message.answer_photo(photo, caption=text, parse_mode="Markdown", reply_markup=kb)
            try:
                await cb.message.delete()
            except Exception:
                pass
    except Exception:
        try:
            await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        except Exception:
            await cb.message.answer(text, parse_mode="Markdown", reply_markup=kb)
            try:
                await cb.message.delete()
            except Exception:
                pass
    await cb.answer()


@router.message(Command("sub"))
async def cmd_sub(msg: Message):
    """Команда /sub — переход в «Мои подписки»."""
    user = await get_or_create_user(msg.from_user.id)
    token = user.get("subscription_token")
    expires_at = user.get("subscription_expires_at")
    personal_sub_url = await _sub_url_for_user(msg.from_user.id)

    now = int(time_module.time())
    if token and expires_at and expires_at > now and personal_sub_url:
        text = build_my_subscriptions_text(personal_sub_url, expires_at, platform=None)
        kb = device_selection_keyboard()
    else:
        text = (
            "📱 *Мои подписки*\n\n"
            "Подписка не активна.\n\n"
            "Купите подписку в разделе «Купить подписку»."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📦 Купить подписку", callback_data="buy_sub")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
            ]
        )

    await msg.answer(text, parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data == "my_subscriptions")
async def show_my_subscriptions(cb: CallbackQuery):
    """Мои подписки: выбор устройства → HTTPS-импорт."""
    user = await get_or_create_user(cb.from_user.id)
    token = user.get("subscription_token")
    expires_at = user.get("subscription_expires_at")
    personal_sub_url = await _sub_url_for_user(cb.from_user.id)

    now = int(time_module.time())
    if token and expires_at and expires_at > now and personal_sub_url:
        text = build_my_subscriptions_text(personal_sub_url, expires_at, platform=None)
        kb = device_selection_keyboard()
    else:
        text = (
            "📱 *Мои подписки*\n\n"
            "Подписка не активна.\n\n"
            "Купите подписку в разделе «Купить подписку»."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📦 Купить подписку", callback_data="buy_sub")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
            ]
        )

    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="Markdown")
    await cb.answer()


@router.callback_query(F.data.startswith("subdev:"))
async def handle_subdev_step(cb: CallbackQuery):
    """Выбор устройства: android / ios / pc или возврат subdev:menu."""
    data = cb.data or ""
    if data == "subdev:menu":
        user = await get_or_create_user(cb.from_user.id)
        token = user.get("subscription_token")
        expires_at = user.get("subscription_expires_at")
        personal_sub_url = await _sub_url_for_user(cb.from_user.id)
        now = int(time_module.time())
        if not (token and expires_at and expires_at > now and personal_sub_url):
            await cb.answer("Подписка не активна", show_alert=True)
            return
        text = build_my_subscriptions_text(personal_sub_url, expires_at, platform=None)
        await _safe_edit_message(cb, text, reply_markup=device_selection_keyboard(), parse_mode="Markdown")
        await cb.answer()
        return

    platform = data.split(":", 1)[1]
    if platform not in ("android", "ios", "pc"):
        await cb.answer()
        return

    user = await get_or_create_user(cb.from_user.id)
    token = user.get("subscription_token")
    expires_at = user.get("subscription_expires_at")
    personal_sub_url = await _sub_url_for_user(cb.from_user.id)
    now = int(time_module.time())
    if not (token and expires_at and expires_at > now and personal_sub_url):
        await cb.answer("Подписка не активна", show_alert=True)
        return

    text = build_my_subscriptions_text(personal_sub_url, expires_at, platform=platform)
    if not IMPORT_BRIDGE_BASE:
        text += (
            "\n\n⚠️ Для кнопок импорта задайте на сервере переменную *PUBLIC_BASE_URL* "
            "(или *IMPORT_BRIDGE_BASE*) — адрес, где доступен этот бот по HTTPS."
        )
    kb = app_import_keyboard(platform, personal_sub_url)
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="Markdown")
    await cb.answer()
