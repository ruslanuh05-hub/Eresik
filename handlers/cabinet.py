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
    FSInputFile,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command

from database import get_or_create_user
from config import (
    CABINET_PREMIUM_EMOJI,
    IMPORT_BRIDGE_BASE,
    PUBLIC_BASE_URL,
    UPSTREAM_SUB_URL,
    PROFILE_IMAGE,
)
from tgemoji import E, tg
from handlers.keyboards_common import back_btn, row_back_main
from handlers.ui_nav import apply_screen_from_callback

logger = logging.getLogger("jvpn-bot.cabinet")
router = Router()


async def _safe_edit_message(cb: CallbackQuery, text: str, reply_markup=None, parse_mode: str = "HTML"):
    """Редактирование экрана: при фото — смена на приветственное изображение + подпись."""
    await apply_screen_from_callback(
        cb,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        photo_mode="subs",
    )


def device_selection_keyboard() -> InlineKeyboardMarkup:
    """Шаг 1: выбор устройства (Android | iOS / ПК), премиум-иконки на кнопках."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 Android",
                    callback_data="subdev:android",
                    icon_custom_emoji_id=E.ANDROID_ROBOT,
                ),
                InlineKeyboardButton(
                    text="🍏 iOS",
                    callback_data="subdev:ios",
                    icon_custom_emoji_id=E.IOS_APPLE,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💻 ПК",
                    callback_data="subdev:pc",
                    icon_custom_emoji_id=E.PC_LAPTOP,
                )
            ],
            [back_btn(callback_data="connect_menu", text="Назад")],
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
                [back_btn(callback_data="subdev:menu", text="К устройствам")],
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
    rows.append([back_btn(callback_data="subdev:menu", text="К устройствам")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cabinet_keyboard() -> InlineKeyboardMarkup:
    """Профиль: подключение через «Мои подписки», без отображения URL."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подключиться",
                    callback_data="my_subscriptions",
                    icon_custom_emoji_id=E.MOLNY,
                ),
            ],
            row_back_main(),
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


def _telegram_error_soft_fail(msg: str) -> bool:
    """Ошибки, после которых имеет смысл тихо перейти на запасной вариант текста."""
    m = msg.lower()
    return any(
        x in m
        for x in (
            "document_invalid",
            "can't parse",
            "cannot parse",
            "parse entities",
            "entity",
        )
    )


def _cabinet_caption_attempts(user: dict, telegram_id: int) -> list[tuple[str, str | None]]:
    """Варианты подписи профиля (HTML с премиум-эмодзи → HTML → plain)."""
    attempts: list[tuple[str, str | None]] = []
    if CABINET_PREMIUM_EMOJI:
        attempts.append((_cabinet_html(user, telegram_id, rich_emoji=True), "HTML"))
    attempts.extend(
        [
            (_cabinet_html(user, telegram_id, rich_emoji=False), "HTML"),
            (_cabinet_plaintext(user, telegram_id), None),
        ]
    )
    return attempts


async def _deliver_cabinet(
    bot,
    chat_id: int,
    telegram_user_id: int,
    *,
    reply_markup,
    photo_bytes: bytes | None = None,
) -> None:
    """
    Отправить профиль в чат (надёжно при InaccessibleMessage).

    Если передан photo_bytes — одно сообщение «фото + подпись» с клавиатурой.
    Иначе только текст.

    По умолчанию без <tg-emoji> в тексте: см. CABINET_PREMIUM_EMOJI в config.
    """
    user = await get_or_create_user(telegram_user_id)
    attempts = _cabinet_caption_attempts(user, telegram_user_id)
    last_err: TelegramBadRequest | None = None
    for i, (text, parse_mode) in enumerate(attempts):
        try:
            if photo_bytes is not None:
                photo = BufferedInputFile(photo_bytes, filename="cabinet.png")
                if parse_mode:
                    await bot.send_photo(
                        chat_id,
                        photo,
                        caption=text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup,
                    )
                else:
                    await bot.send_photo(
                        chat_id,
                        photo,
                        caption=text,
                        reply_markup=reply_markup,
                    )
            elif parse_mode:
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
            err_s = str(e)
            is_last = i == len(attempts) - 1
            soft = _telegram_error_soft_fail(err_s)
            action = "send_photo" if photo_bytes is not None else "send_message"
            if soft and not is_last:
                logger.debug(
                    "cabinet: %s fallback next (parse_mode=%r): %s",
                    action,
                    parse_mode,
                    e,
                )
            else:
                logger.warning(
                    "cabinet: %s failed (parse_mode=%r): %s",
                    action,
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
        await _deliver_cabinet(
            msg.bot,
            msg.chat.id,
            msg.from_user.id,
            reply_markup=kb,
            photo_bytes=PROFILE_IMAGE.read_bytes() if PROFILE_IMAGE.exists() else None,
        )
    except Exception:
        logger.exception("cmd_my: _deliver_cabinet failed")
        await msg.answer(
            "Не удалось открыть профиль. Попробуйте позже или обратитесь в поддержку.",
        )


@router.callback_query(F.data == "cabinet")
async def show_cabinet(cb: CallbackQuery):
    """Профиль: в том же сообщении с фото — смена медиа на фон кабинета + подпись."""
    await cb.answer()
    uid = cb.from_user.id
    kb = cabinet_keyboard()
    try:
        user = await get_or_create_user(uid)
        msg = cb.message
        attempts = _cabinet_caption_attempts(user, uid)

        if msg:
            if msg.photo and PROFILE_IMAGE.exists():
                for i, (text, pmode) in enumerate(attempts):
                    try:
                        if pmode:
                            await msg.edit_media(
                                InputMediaPhoto(
                                    media=FSInputFile(PROFILE_IMAGE),
                                    caption=text,
                                    parse_mode=pmode,
                                ),
                                reply_markup=kb,
                            )
                        else:
                            await msg.edit_media(
                                InputMediaPhoto(
                                    media=FSInputFile(PROFILE_IMAGE),
                                    caption=text,
                                ),
                                reply_markup=kb,
                            )
                        return
                    except TelegramBadRequest as e:
                        err_s = str(e)
                        is_last = i == len(attempts) - 1
                        if _telegram_error_soft_fail(err_s) and not is_last:
                            logger.debug(
                                "show_cabinet: edit_media fallback next (parse_mode=%r): %s",
                                pmode,
                                e,
                            )
                            continue
                        logger.warning(
                            "show_cabinet: edit_media failed (parse_mode=%r): %s",
                            pmode,
                            e,
                        )

            for i, (text, pmode) in enumerate(attempts):
                try:
                    if msg.caption is not None:
                        if pmode:
                            await msg.edit_caption(caption=text, parse_mode=pmode, reply_markup=kb)
                        else:
                            await msg.edit_caption(caption=text, reply_markup=kb)
                    else:
                        if pmode:
                            await msg.edit_text(text, parse_mode=pmode, reply_markup=kb)
                        else:
                            await msg.edit_text(text, reply_markup=kb)
                    return
                except TelegramBadRequest as e:
                    err_s = str(e)
                    is_last = i == len(attempts) - 1
                    if _telegram_error_soft_fail(err_s) and not is_last:
                        logger.debug(
                            "show_cabinet: edit caption/text fallback next (parse_mode=%r): %s",
                            pmode,
                            e,
                        )
                        continue
                    logger.warning(
                        "show_cabinet: edit caption/text failed (parse_mode=%r): %s",
                        pmode,
                        e,
                    )
                except Exception:
                    logger.exception("show_cabinet: unexpected edit error")

        # Fallback: отправить профиль новым сообщением пользователю.
        await _deliver_cabinet(
            cb.bot,
            uid,
            uid,
            reply_markup=kb,
            photo_bytes=PROFILE_IMAGE.read_bytes() if PROFILE_IMAGE.exists() else None,
        )
    except Exception:
        logger.exception("show_cabinet: fatal error")
        try:
            await cb.bot.send_message(
                uid,
                "Не удалось открыть профиль. Попробуйте ещё раз или отправьте команду /my",
            )
        except Exception:
            pass


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
                [
                    InlineKeyboardButton(
                        text="Купить подписку",
                        callback_data="buy_sub:subs",
                        icon_custom_emoji_id=E.INSTRUCTION_BOOKMARK,
                    ),
                ],
                [back_btn(callback_data="connect_menu", text="Назад")],
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
                [
                    InlineKeyboardButton(
                        text="Купить подписку",
                        callback_data="buy_sub:subs",
                        icon_custom_emoji_id=E.INSTRUCTION_BOOKMARK,
                    ),
                ],
                [back_btn(callback_data="connect_menu", text="Назад")],
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
