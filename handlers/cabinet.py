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

logger = logging.getLogger("jvpn-bot.cabinet")
router = Router()


async def _send_subs_screen(cb: CallbackQuery, text: str, reply_markup, parse_mode: str = "HTML"):
    """
    Показать экран подписок в том же сообщении.

    Приоритет:
    1) редактирование текущего сообщения (не плодим новые сообщения на «Назад»),
    2) fallback на send_message, если edit невозможен.
    """
    uid = cb.from_user.id
    msg = cb.message

    # 1) Пытаемся обновить текущее сообщение.
    if msg:
        for use_markup in (True, False):
            for pm in (parse_mode, None):
                try:
                    kb = reply_markup if use_markup else None
                    if getattr(msg, "photo", None):
                        if pm:
                            await msg.edit_caption(caption=text, parse_mode=pm, reply_markup=kb)
                        else:
                            await msg.edit_caption(caption=text, reply_markup=kb)
                    else:
                        if pm:
                            await msg.edit_text(text, parse_mode=pm, reply_markup=kb)
                        else:
                            await msg.edit_text(text, reply_markup=kb)
                    return
                except Exception as e:
                    # Это не ошибка: экран уже такой же, не уходим в fallback без HTML.
                    if "message is not modified" in str(e).lower():
                        return
                    if use_markup or pm:
                        logger.debug("_send_subs_screen edit retry (markup=%s, pm=%s): %s", use_markup, pm, e)
                    else:
                        logger.debug("_send_subs_screen edit failed, switch to send_message: %s", e)

    # 2) Fallback: отправляем новым сообщением.
    for use_markup in (True, False):
        for pm in (parse_mode, None):
            try:
                kb = reply_markup if use_markup else None
                await cb.bot.send_message(uid, text, parse_mode=pm, reply_markup=kb)
                return
            except Exception as e:
                if "message is not modified" in str(e).lower():
                    return
                if use_markup or pm:
                    logger.debug("_send_subs_screen retry (markup=%s, pm=%s): %s", use_markup, pm, e)
                else:
                    logger.exception("_send_subs_screen failed")
                    raise


def _plain_back_btn(callback_data: str, text: str = "Назад") -> InlineKeyboardButton:
    """Кнопка «Назад» с premium-стрелкой."""
    return InlineKeyboardButton(text=text, callback_data=callback_data, icon_custom_emoji_id=E.BACKARROW)


def device_selection_keyboard(has_sub_url: bool = False) -> InlineKeyboardMarkup:
    """Шаг 1: выбор устройства (Android | iOS / ПК)."""
    rows = [
        [
            InlineKeyboardButton(text="🤖 Android", callback_data="subdev:android"),
            InlineKeyboardButton(text="🍏 iOS", callback_data="subdev:ios"),
        ],
        [
            InlineKeyboardButton(text="💻 ПК", callback_data="subdev:pc"),
        ],
    ]
    if has_sub_url:
        rows.append([InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="sub:copy_link")])
    rows.append([_plain_back_btn("buy_sub", "Назад")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _bridge_url(app: str, personal_sub_url: str) -> str:
    base = (IMPORT_BRIDGE_BASE or "").rstrip("/")
    return f"{base}/open/{app}?u={quote(personal_sub_url, safe='')}"


def _deep_link_url(app: str, personal_sub_url: str) -> str:
    encoded = quote(personal_sub_url, safe="")
    if app == "v2raytun":
        return f"v2raytun://import/{encoded}"
    if app == "happ":
        return f"happ://import/{encoded}"
    if app == "hiddify":
        return f"hiddify://import/{encoded}#JetVPN"
    return personal_sub_url


def app_import_keyboard(platform: str, personal_sub_url: str) -> InlineKeyboardMarkup:
    """
    Шаг 2: кнопки-ссылки на HTTPS-страницу /open/... (редирект в приложение).
    Android / iOS: v2RayTun | Happ; ПК: Hiddify | Happ.
    """
    if not personal_sub_url:
        return InlineKeyboardMarkup(
            inline_keyboard=[[_plain_back_btn("subdev:menu", "К устройствам")]],
        )

    rows = []
    def _link(app: str) -> str | None:
        # Telegram url= только http/https.
        if IMPORT_BRIDGE_BASE:
            u = _bridge_url(app, personal_sub_url)
        elif personal_sub_url and personal_sub_url.startswith("https://"):
            u = personal_sub_url
        else:
            u = personal_sub_url or ""
        return u if u.startswith("https://") and len(u) < 500 else None

    def _url_btn(text: str, app: str) -> InlineKeyboardButton | None:
        url = _link(app)
        return InlineKeyboardButton(text=text, url=url) if url else None

    if platform in ("android", "ios"):
        btns = [_url_btn("📱 v2RayTun", "v2raytun"), _url_btn("📱 Happ", "happ")]
        if any(btns):
            rows.append([b for b in btns if b is not None])
    elif platform == "pc":
        btns = [_url_btn("💻 Hiddify", "hiddify"), _url_btn("📱 Happ", "happ")]
        if any(btns):
            rows.append([b for b in btns if b is not None])
    rows.append([_plain_back_btn("subdev:menu", "К устройствам")])
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
            [
                InlineKeyboardButton(
                    text="Продлить подписку",
                    callback_data="renew_sub",
                    icon_custom_emoji_id=E.INSTRUCTION_BOOKMARK,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Реферальная программа",
                    callback_data="referrals",
                    icon_custom_emoji_id=E.MONEY,
                )
            ],
            row_back_main(),
        ]
    )


def my_subscriptions_actions_keyboard(is_active: bool) -> InlineKeyboardMarkup:
    """Кнопки для экрана «Мои подписки» в требуемом порядке."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="Купить подписку",
                callback_data="buy_sub:subs",
                icon_custom_emoji_id=E.GIFT,
            )
        ]
    ]
    if is_active:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Продлить",
                    callback_data="renew_sub",
                    icon_custom_emoji_id=E.MONEY,
                )
            ]
        )
        # Для удобства подключения показываем выбор устройства прямо в «Мои подписки».
        rows.append(
            [
                InlineKeyboardButton(
                    text="К устройствам",
                    callback_data="subdev:menu",
                    icon_custom_emoji_id=E.MOLNY,
                )
            ]
        )
    rows.append([back_btn(callback_data="connect_menu", text="Назад")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
        "android": "🤖 Android",
        "ios": "🍏 iOS",
        "pc": "💻 ПК",
    }.get(platform, platform)


def build_purchase_success_text(plan_title: str, expires_at: int) -> str:
    """Текст после успешной покупки (без URL — импорт только кнопками)."""
    return (
        "✅ <b>Подписка активирована!</b>\n\n"
        f"Тариф: {escape(plan_title)}\n\n"
        f"🗓️ Действует до: {_format_date(expires_at)}\n"
        f"🕒 Осталось: {_format_expires(expires_at)}\n\n"
        "Выберите устройство и приложение — импорт откроется по кнопкам ниже."
    )


def build_my_subscriptions_text(
    expires_at: int,
    platform: str | None = None,
) -> str:
    """Текст экрана «Мои подписки» (без URL)."""
    base = (
        f'{tg(E.PARTY, "🎉")} <b>Мои подписки</b>\n\n'
        f"🗓️ Действует до: {_format_date(expires_at)}\n"
        f"🕒 Осталось: {_format_expires(expires_at)}\n\n"
    )
    if platform is None:
        return base + "Управляйте подпиской кнопками ниже:"
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
        kb = my_subscriptions_actions_keyboard(is_active=True)
    else:
        text = (
            f'{tg(E.PARTY, "🎉")} <b>Мои подписки</b>\n\n'
            "Подписка не активна.\n\n"
            "Купите подписку в разделе «Купить подписку»."
        )
        kb = my_subscriptions_actions_keyboard(is_active=False)

    await msg.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "my_subscriptions")
async def show_my_subscriptions(cb: CallbackQuery):
    """Мои подписки: выбор устройства → HTTPS-импорт."""
    await cb.answer()
    try:
        user = await get_or_create_user(cb.from_user.id)
        token = user.get("subscription_token")
        expires_at = user.get("subscription_expires_at")
        personal_sub_url = await _sub_url_for_user(cb.from_user.id)

        now = int(time_module.time())
        if token and expires_at and expires_at > now and personal_sub_url:
            text = build_my_subscriptions_text(expires_at, platform=None)
            kb = my_subscriptions_actions_keyboard(is_active=True)
        else:
            text = (
                f'{tg(E.PARTY, "🎉")} <b>Мои подписки</b>\n\n'
                "Подписка не активна.\n\n"
                "Купите подписку в разделе «Купить подписку»."
            )
            kb = my_subscriptions_actions_keyboard(is_active=False)

        await _send_subs_screen(cb, text, kb, parse_mode="HTML")
    except Exception:
        logger.exception("show_my_subscriptions failed")
        try:
            await cb.bot.send_message(
                cb.from_user.id,
                "Не удалось открыть раздел. Попробуйте команду /sub или /start.",
            )
        except Exception:
            pass


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
        await cb.answer()
        text = build_my_subscriptions_text(expires_at, platform=None)
        await _send_subs_screen(cb, text, device_selection_keyboard(has_sub_url=True), parse_mode="HTML")
        return

    platform = data.split(":", 1)[1]
    if platform not in ("android", "ios", "pc"):
        await cb.answer()
        return

    try:
        user = await get_or_create_user(cb.from_user.id)
        token = user.get("subscription_token")
        expires_at = user.get("subscription_expires_at")
        personal_sub_url = await _sub_url_for_user(cb.from_user.id)
        now = int(time_module.time())
        if not (token and expires_at and expires_at > now and personal_sub_url):
            await cb.answer("Подписка не активна", show_alert=True)
            return

        await cb.answer()
        text = build_my_subscriptions_text(expires_at, platform=platform)
        kb = app_import_keyboard(platform, personal_sub_url)
        await _send_subs_screen(cb, text, kb, parse_mode="HTML")
    except Exception:
        logger.exception("handle_subdev_step failed")
        try:
            await cb.bot.send_message(
                cb.from_user.id,
                "Не удалось открыть экран. Проверьте, что подписка активна, и попробуйте /sub.",
            )
        except Exception:
            pass


@router.callback_query(F.data == "sub:copy_link")
async def copy_subscription_link(cb: CallbackQuery):
    """Отправить персональную ссылку подписки для копирования."""
    await cb.answer()
    try:
        personal_sub_url = await _sub_url_for_user(cb.from_user.id)
        if not personal_sub_url:
            await cb.answer("Подписка не активна", show_alert=True)
            return
        await cb.bot.send_message(
            cb.from_user.id,
            "📋 <b>Ссылка для подключения</b>\n\n"
            "Скопируйте ссылку ниже:\n"
            f"<code>{escape(personal_sub_url)}</code>",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("copy_subscription_link failed")
        try:
            await cb.bot.send_message(cb.from_user.id, "Не удалось получить ссылку. Попробуйте позже.")
        except Exception:
            pass
