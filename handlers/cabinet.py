"""Личный кабинет пользователя."""

import logging
import time as time_module
from html import escape
from urllib.parse import quote

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    Message,
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command

from database import get_or_create_user
from image_gen import generate_subscription_image
from config import IMPORT_BRIDGE_BASE, PUBLIC_BASE_URL, UPSTREAM_SUB_URL
from tgemoji import E, tg

logger = logging.getLogger("jvpn-bot.cabinet")
router = Router()


async def _safe_edit_message(cb: CallbackQuery, text: str, reply_markup=None, parse_mode: str = "HTML"):
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
    """Шаг 1: выбор устройства (Android | iOS / ПК), премиум-иконки на кнопках."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="ANDROID",
                    callback_data="subdev:android",
                    icon_custom_emoji_id=E.ANDROID_ROBOT,
                ),
                InlineKeyboardButton(
                    text="iOS",
                    callback_data="subdev:ios",
                    icon_custom_emoji_id=E.IOS_APPLE,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="ПК",
                    callback_data="subdev:pc",
                    icon_custom_emoji_id=E.PC_LAPTOP,
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="connect_menu")],
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
    """Профиль: подключение через «Мои подписки», без отображения URL."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Подключиться", callback_data="my_subscriptions")],
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
    return {
        "android": f'{tg(E.ANDROID_ROBOT, "🤖")} Android',
        "ios": f'{tg(E.IOS_APPLE, "🍏")} iOS',
        "pc": f'{tg(E.PC_LAPTOP, "💻")} ПК',
    }.get(platform, platform)


def build_purchase_success_text(plan_title: str, expires_at: int) -> str:
    """Текст после успешной покупки (без URL — импорт только кнопками)."""
    return (
        "✅ <b>Подписка активирована!</b>\n\n"
        f"Тариф: {escape(plan_title)}\n\n"
        f'{tg(E.CALENDAR, "🗓️")} Действует до: {_format_date(expires_at)}\n'
        f'{tg(E.CLOCK, "🕒")} Осталось: {_format_expires(expires_at)}\n\n'
        "Выберите устройство и приложение — импорт откроется по кнопкам ниже."
    )


def build_my_subscriptions_text(
    expires_at: int,
    platform: str | None = None,
) -> str:
    """Текст экрана «Мои подписки» (без URL)."""
    base = (
        "📱 <b>Мои подписки</b>\n\n"
        f'{tg(E.CALENDAR, "🗓️")} Действует до: {_format_date(expires_at)}\n'
        f'{tg(E.CLOCK, "🕒")} Осталось: {_format_expires(expires_at)}\n\n'
    )
    if platform is None:
        return base + "Выберите устройство:"
    return (
        base
        + f"{_platform_title(platform)}\n\n"
        + "Выберите приложение — откроется страница импорта в браузере:"
    )


def _cabinet_html(user: dict, telegram_id: int, *, rich_emoji: bool) -> str:
    """Текст профиля (HTML)."""
    try:
        balance = float(user.get("balance") or 0)
    except (TypeError, ValueError):
        balance = 0.0
    expires_at = user.get("subscription_expires_at")
    nickname = user.get("nickname") or user.get("username") or f"user_{telegram_id}"
    nick_safe = escape(nickname)

    if not rich_emoji:
        return (
            "👤 <b>Личный кабинет</b>\n\n"
            f"👤 Ник: <code>{nick_safe}</code>\n"
            f"💰 Баланс: <b>{balance:.2f} ₽</b>\n"
            f"🗓️ Подписка до: {_format_date(expires_at)}\n"
            f"🕒 Осталось: {_format_expires(expires_at)}\n"
        )

    return (
        f'{tg(E.USER_HEADER, "👤")} <b>Личный кабинет</b>\n\n'
        f'{tg(E.USER_NICK, "👤")} Ник: <code>{nick_safe}</code>\n'
        f'{tg(E.MONEY, "💰")} Баланс: <b>{balance:.2f} ₽</b>\n'
        f'{tg(E.CALENDAR, "🗓️")} Подписка до: {_format_date(expires_at)}\n'
        f'{tg(E.CLOCK, "🕒")} Осталось: {_format_expires(expires_at)}\n'
    )


def _cabinet_plaintext(user: dict, telegram_id: int) -> str:
    """Профиль без HTML (если Telegram отклоняет разметку)."""
    try:
        balance = float(user.get("balance") or 0)
    except (TypeError, ValueError):
        balance = 0.0
    expires_at = user.get("subscription_expires_at")
    nickname = user.get("nickname") or user.get("username") or f"user_{telegram_id}"
    return (
        "Личный кабинет\n\n"
        f"Ник: {nickname}\n"
        f"Баланс: {balance:.2f} ₽\n"
        f"Подписка до: {_format_date(expires_at)}\n"
        f"Осталось: {_format_expires(expires_at)}\n"
    )


async def build_cabinet_text(telegram_id: int, *, rich_emoji: bool = True) -> str:
    """Текст профиля (для совместимости)."""
    user = await get_or_create_user(telegram_id)
    return _cabinet_html(user, telegram_id, rich_emoji=rich_emoji)


async def _deliver_cabinet(
    bot,
    chat_id: int,
    telegram_user_id: int,
    *,
    reply_markup,
) -> None:
    """
    Отправить профиль в чат. Используем bot.send_message (надёжно при InaccessibleMessage).
    Несколько попыток: HTML+tg-emoji → HTML без tg-emoji → простой текст.
    """
    user = await get_or_create_user(telegram_user_id)
    attempts: list[tuple[str, str | None]] = [
        (_cabinet_html(user, telegram_user_id, rich_emoji=True), "HTML"),
        (_cabinet_html(user, telegram_user_id, rich_emoji=False), "HTML"),
        (_cabinet_plaintext(user, telegram_user_id), None),
    ]
    last_err: TelegramBadRequest | None = None
    for text, parse_mode in attempts:
        try:
            if parse_mode:
                await bot.send_message(
                    chat_id,
                    text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            else:
                await bot.send_message(chat_id, text, reply_markup=reply_markup)
            return
        except TelegramBadRequest as e:
            last_err = e
            logger.warning(
                "cabinet: send_message failed (parse_mode=%r): %s",
                parse_mode,
                e,
            )
    if last_err:
        raise last_err


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

    kb = cabinet_keyboard()
    try:
        await _deliver_cabinet(msg.bot, msg.chat.id, msg.from_user.id, reply_markup=kb)
    except Exception:
        logger.exception("cmd_my: _deliver_cabinet failed")
        await msg.answer(
            "Не удалось открыть профиль. Попробуйте позже или обратитесь в поддержку.",
        )
        return
    try:
        img_bytes = generate_subscription_image(
            user.get("subscription_expires_at"),
            user.get("nickname") or msg.from_user.username or "",
        )
        photo = BufferedInputFile(img_bytes, filename="cabinet.png")
        await msg.bot.send_photo(msg.chat.id, photo)
    except Exception:
        logger.exception("cmd_my: cabinet image failed (text already sent)")


@router.callback_query(F.data == "cabinet")
async def show_cabinet(cb: CallbackQuery):
    """Профиль: send_message в чат пользователя (не reply на сообщение — работает с InaccessibleMessage)."""
    await cb.answer()
    uid = cb.from_user.id
    user = await get_or_create_user(uid)
    kb = cabinet_keyboard()
    try:
        await _deliver_cabinet(cb.bot, uid, uid, reply_markup=kb)
    except Exception:
        logger.exception("show_cabinet: _deliver_cabinet failed")
        try:
            await cb.bot.send_message(
                uid,
                "Не удалось открыть профиль. Напишите команду /my",
            )
        except Exception:
            pass
        return
    try:
        img_bytes = generate_subscription_image(
            user.get("subscription_expires_at"),
            user.get("nickname") or cb.from_user.username or "",
        )
        photo = BufferedInputFile(img_bytes, filename="cabinet.png")
        await cb.bot.send_photo(uid, photo)
    except Exception:
        logger.exception("cabinet: image failed after text (profile text already shown)")
    if isinstance(cb.message, Message):
        try:
            await cb.message.delete()
        except Exception as del_err:
            logger.debug("cabinet: could not delete old message: %s", del_err)


@router.message(Command("sub"))
async def cmd_sub(msg: Message):
    """Команда /sub — переход в «Мои подписки»."""
    user = await get_or_create_user(msg.from_user.id)
    token = user.get("subscription_token")
    expires_at = user.get("subscription_expires_at")
    personal_sub_url = await _sub_url_for_user(msg.from_user.id)

    now = int(time_module.time())
    if token and expires_at and expires_at > now and personal_sub_url:
        text = build_my_subscriptions_text(expires_at, platform=None)
        kb = device_selection_keyboard()
    else:
        text = (
            "📱 <b>Мои подписки</b>\n\n"
            "Подписка не активна.\n\n"
            "Купите подписку в разделе «Купить подписку»."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📦 Купить подписку", callback_data="buy_sub:subs")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="connect_menu")],
            ]
        )

    await msg.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "my_subscriptions")
async def show_my_subscriptions(cb: CallbackQuery):
    """Мои подписки: выбор устройства → HTTPS-импорт."""
    user = await get_or_create_user(cb.from_user.id)
    token = user.get("subscription_token")
    expires_at = user.get("subscription_expires_at")
    personal_sub_url = await _sub_url_for_user(cb.from_user.id)

    now = int(time_module.time())
    if token and expires_at and expires_at > now and personal_sub_url:
        text = build_my_subscriptions_text(expires_at, platform=None)
        kb = device_selection_keyboard()
    else:
        text = (
            "📱 <b>Мои подписки</b>\n\n"
            "Подписка не активна.\n\n"
            "Купите подписку в разделе «Купить подписку»."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📦 Купить подписку", callback_data="buy_sub:subs")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="connect_menu")],
            ]
        )

    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML")
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
        text = build_my_subscriptions_text(expires_at, platform=None)
        await _safe_edit_message(cb, text, reply_markup=device_selection_keyboard(), parse_mode="HTML")
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

    text = build_my_subscriptions_text(expires_at, platform=platform)
    if not IMPORT_BRIDGE_BASE:
        text += (
            "\n\n⚠️ Для кнопок импорта задайте на сервере переменную <b>PUBLIC_BASE_URL</b> "
            "(или <b>IMPORT_BRIDGE_BASE</b>) — адрес, где доступен этот бот по HTTPS."
        )
    kb = app_import_keyboard(platform, personal_sub_url)
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()
