"""Команды /start и главное меню."""
import logging
import random
from html import escape

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)

from database import apply_referral_bonus, get_or_create_user, get_user_by_telegram_id
from tgemoji import E, tg
from config import (
    WELCOME_IMAGE,
    SUPPORT_USERNAME,
    PRIVACY_POLICY_URL,
    TERMS_URL,
    CONTACT_INFO_URL,
    GUIDE_ANDROID_URL,
    GUIDE_IOS_URL,
    GUIDE_ANDROID_TV_URL,
    GUIDE_PC_URL,
    GUIDE_ANDROID_VIDEO,
    GUIDE_IOS_VIDEO,
    GUIDE_ANDROID_TV_VIDEO,
    GUIDE_PC_VIDEO,
    SUBSCRIBE_CHANNEL_USERNAME,
    SUBSCRIBE_CHANNEL_URL,
)
from handlers.keyboards_common import markup_back_main_only, row_back_main
from handlers.ui_nav import apply_screen_from_callback

logger = logging.getLogger("jvpn-bot.start")

router = Router()


class ReferralCaptcha(StatesGroup):
    waiting = State()


# Эмодзи для проверки (только при первом /start по ссылке ref_*)
_REF_CAPTCHA_EMOJIS: list[tuple[str, str]] = [
    (E.PARTY, "🎉"),
    (E.GIFT, "🎁"),
    (E.MOLNY, "⚡️"),
    (E.HEART, "💜"),
]


def _build_ref_captcha_keyboard() -> tuple[InlineKeyboardMarkup, str, str]:
    """Клавиатура 2×2: ровно один совпадает с подсказкой в тексте."""
    correct_id, fb = random.choice(_REF_CAPTCHA_EMOJIS)
    order = _REF_CAPTCHA_EMOJIS.copy()
    random.shuffle(order)
    rows: list[list[InlineKeyboardButton]] = []
    pair: list[InlineKeyboardButton] = []
    for eid, _ in order:
        pair.append(
            InlineKeyboardButton(
                text="·",
                callback_data=f"refpick:{eid}",
                icon_custom_emoji_id=eid,
            )
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    return InlineKeyboardMarkup(inline_keyboard=rows), correct_id, fb


async def _is_user_subscribed(bot, user_id: int) -> bool:
    """
    Проверить подписку на канал/чат по username.
    Если API Telegram отдаёт ошибку — считаем что не подписан.
    """
    try:
        # aiogram v3: get_chat_member(chat_id=..., user_id=...)
        member = await bot.get_chat_member(chat_id=f"@{SUBSCRIBE_CHANNEL_USERNAME}", user_id=user_id)
        return getattr(member, "status", None) in ("member", "administrator", "creator")
    except Exception:
        return False


async def _strip_reply_keyboard(bot, chat_id: int) -> None:
    """Убрать старую reply-клавиатуру у пользователя (если была)."""
    try:
        m = await bot.send_message(chat_id, "\u2060", reply_markup=ReplyKeyboardRemove())
        await bot.delete_message(chat_id, m.message_id)
    except Exception:
        logger.debug("strip reply keyboard skipped", exc_info=True)


async def _safe_edit_message(
    cb: CallbackQuery,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
    photo_mode: str = "welcome",
):
    """Редактирование экрана: меняем caption и фото по `photo_mode`."""
    await apply_screen_from_callback(
        cb,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        photo_mode=photo_mode,
    )


def main_menu_inline() -> InlineKeyboardMarkup:
    """Главное меню: только inline, все иконки — премиум (icon_custom_emoji_id)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подключиться",
                    callback_data="connect_menu",
                    icon_custom_emoji_id=E.MOLNY,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Профиль",
                    callback_data="cabinet",
                    icon_custom_emoji_id=E.PROF,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="О нас",
                    callback_data="about",
                    icon_custom_emoji_id=E.FORME,
                ),
                InlineKeyboardButton(
                    text="Поддержка",
                    callback_data="support",
                    icon_custom_emoji_id=E.SUPPORT_BOT,
                ),
            ],
        ]
    )


def connect_keyboard() -> InlineKeyboardMarkup:
    """Окно «Подключиться»: Моя подписка, Купить, Пополнить + Назад в главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Мои подписки",
                    callback_data="my_subscriptions",
                    icon_custom_emoji_id=E.PARTY,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Купить подписку",
                    callback_data="buy_sub",
                    icon_custom_emoji_id=E.GIFT,
                ),
            ],
            [                
                InlineKeyboardButton(
                    text="Пополнить баланс",
                    callback_data="topup",
                    icon_custom_emoji_id=E.MONEY,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Реферальная программа",
                    callback_data="referrals",
                    icon_custom_emoji_id=E.MONEY,
                ),
            ],
            row_back_main(),
        ]
    )


def _welcome_text() -> str:
    return (
        f'{tg(E.HEART, "💜")} <b>Добро пожаловать в JetVPN!</b>\n\n'
        f'Выберите действие {tg(E.ARROW_DOWN, "⬇️")}'
    )


async def _deliver_welcome(bot, chat_id: int) -> None:
    """Отправить главное меню (как после /start)."""
    await _strip_reply_keyboard(bot, chat_id)
    text = _welcome_text()
    kb = main_menu_inline()
    if WELCOME_IMAGE.exists():
        photo = FSInputFile(WELCOME_IMAGE)
        await bot.send_photo(
            chat_id,
            photo,
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    else:
        await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _send_welcome(msg: Message) -> None:
    """Приветствие: снимаем reply-клавиатуру, одно сообщение с inline-меню (+ фото в caption при наличии)."""
    await _deliver_welcome(msg.bot, msg.chat.id)


@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext, command: CommandObject):
    await state.clear()
    existed_before = await get_user_by_telegram_id(msg.from_user.id)
    await get_or_create_user(msg.from_user.id, msg.from_user.username)

    raw = (command.args or "").strip() if command else ""
    if raw.startswith("ref_"):
        try:
            referrer_id = int(raw[4:])
        except ValueError:
            await _send_welcome(msg)
            return
        if referrer_id == msg.from_user.id:
            await _send_welcome(msg)
            return
        # Реферальный бонус — только для нового пользователя (первый вход по ссылке).
        if existed_before:
            await msg.answer(
                "Вы уже были зарегистрированы ранее, поэтому реферальный бонус недоступен.",
                parse_mode=ParseMode.HTML,
            )
            await _send_welcome(msg)
            return
        user = await get_or_create_user(msg.from_user.id, msg.from_user.username)
        if int(user.get("referral_bonus_claimed") or 0):
            await _send_welcome(msg)
            return
        await state.set_state(ReferralCaptcha.waiting)
        kb, correct_id, fb = _build_ref_captcha_keyboard()
        await state.update_data(referrer_id=referrer_id, correct_emoji_id=str(correct_id))
        await msg.answer(
            f'{tg(E.SUPPORT_BOT, "🤖")} <b>Быстрая проверка</b>\n\n'
            f"Нажмите на такой же эмодзи: {tg(correct_id, fb)}\n\n"
            "<i>Нужно только при переходе по реферальной ссылке.</i>",
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )
        return

    await _send_welcome(msg)


@router.callback_query(ReferralCaptcha.waiting, F.data.startswith("refpick:"))
async def referral_captcha_pick(cb: CallbackQuery, state: FSMContext):
    picked = (cb.data or "").split(":", 1)[1].strip()
    data = await state.get_data()
    correct = str(data.get("correct_emoji_id", ""))
    referrer_id = int(data.get("referrer_id") or 0)
    if not picked or not correct or referrer_id <= 0:
        await state.clear()
        await cb.answer()
        await _deliver_welcome(cb.bot, cb.message.chat.id)
        return
    if picked != correct:
        await cb.answer("Неверно. Попробуйте ещё раз.", show_alert=True)
        kb, new_correct_id, fb = _build_ref_captcha_keyboard()
        await state.update_data(correct_emoji_id=str(new_correct_id))
        try:
            await cb.message.edit_text(
                f'{tg(E.SUPPORT_BOT, "🤖")} <b>Быстрая проверка</b>\n\n'
                f"Нажмите на такой же эмодзи: {tg(new_correct_id, fb)}\n\n"
                "<i>Нужно только при переходе по реферальной ссылке.</i>",
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            logger.debug("referral_captcha_pick: edit_text failed", exc_info=True)
        return

    await cb.answer()
    await state.clear()

    # Награда только при наличии подписки.
    if not await _is_user_subscribed(cb.bot, cb.from_user.id):
        await cb.message.answer(
            "Чтобы получить реферальную награду, пожалуйста подпишитесь на канал:\n"
            f"{SUBSCRIBE_CHANNEL_URL}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Подписаться",
                            url=SUBSCRIBE_CHANNEL_URL,
                        )
                    ],
                    [row_back_main()[0]],
                ]
            ),
        )
        await _deliver_welcome(cb.bot, cb.message.chat.id)
        return

    try:
        ok = await apply_referral_bonus(cb.from_user.id, referrer_id)
    except Exception:
        logger.exception("apply_referral_bonus failed")
        ok = False
    if ok:
        await cb.message.answer(
            "✅ <b>Готово!</b>\n\n"
            "Вам начислено <b>+3 дня</b> подписки.\n"
            "Вашему другу — <b>+6 дней</b>.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await cb.message.answer(
            "Реферальный бонус уже был получен ранее или сейчас недоступен.",
            parse_mode=ParseMode.HTML,
        )
    await _deliver_welcome(cb.bot, cb.message.chat.id)


@router.callback_query(F.data == "main_menu")
async def back_to_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.answer()
    text = _welcome_text()
    kb = main_menu_inline()
    uid = cb.from_user.id
    if not cb.message:
        try:
            await cb.bot.send_message(uid, text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            logger.exception("back_to_main: send welcome (no message) failed")
        return
    await apply_screen_from_callback(
        cb,
        text=text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
        photo_mode="welcome",
    )


@router.callback_query(F.data == "connect_menu")
async def show_connect_menu(cb: CallbackQuery):
    text = f'{tg(E.MOLNY, "⚡️")} <b>Подключиться</b>\n\nВыберите действие {tg(E.ARROW_DOWN, "⬇️")}'
    kb = connect_keyboard()
    await apply_screen_from_callback(
        cb,
        text=text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
        photo_mode="connect",
        allow_fallback_send=False,
    )
    await cb.answer()


@router.callback_query(F.data == "referrals")
async def show_referrals(cb: CallbackQuery):
    """Реферальная система (если вызовут по старой ссылке)."""
    await get_or_create_user(cb.from_user.id, cb.from_user.username)
    code = f"ref_{cb.from_user.id}"
    bot_username = (await cb.bot.me()).username
    invite_link = f"https://t.me/{bot_username}?start={code}" if bot_username else "Ссылка недоступна"
    text = (
        f'{tg(E.MONEY, "🪙")} <b>Реферальная система</b>\n\n'
        "Приглашайте друзей по ссылке ниже.\n\n"
        "Когда друг <b>впервые</b> зайдёт по вашей ссылке и пройдёт короткую проверку — "
        "ему будет начислено <b>+3 дня</b> подписки, а вам — <b>+6 дней</b>.\n\n"
        f"Ваш код: <code>{escape(code)}</code>\n"
        f"Ваша ссылка: <code>{escape(invite_link)}</code>\n\n"
        "<i>Проверка нужна только при переходе по реферальной ссылке. Обычный /start без ссылки — без проверки.</i>"
    )
    await _safe_edit_message(cb, text, reply_markup=markup_back_main_only(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "instruction")
async def show_instruction(cb: CallbackQuery):
    """Инструкция по подключению (если вызовут по старой ссылке)."""
    text = (
        f'{tg(E.INSTRUCTION_BOOKMARK, "🔗")} <b>Инструкция по подключению</b>\n\n'
        "Выберите платформу, и я отправлю видео-инструкцию:"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Android",
                    callback_data="instruction:android",
                    icon_custom_emoji_id=E.MOLNY,
                ),
                InlineKeyboardButton(
                    text="iOS",
                    callback_data="instruction:ios",
                    icon_custom_emoji_id=E.MOLNY,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Android TV",
                    callback_data="instruction:android_tv",
                    icon_custom_emoji_id=E.MOLNY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="ПК",
                    callback_data="instruction:pc",
                    icon_custom_emoji_id=E.MOLNY,
                )
            ],
            row_back_main(),
        ]
    )
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data.startswith("instruction:"))
async def send_instruction_video(cb: CallbackQuery):
    """Отправка видео-инструкции по выбранной платформе."""
    platform = cb.data.split(":", 1)[1]
    mapping = {
        "android": ("📱 Android", GUIDE_ANDROID_VIDEO, GUIDE_ANDROID_URL),
        "ios": ("🍏 iOS", GUIDE_IOS_VIDEO, GUIDE_IOS_URL),
        "android_tv": ("📺 Android TV", GUIDE_ANDROID_TV_VIDEO, GUIDE_ANDROID_TV_URL),
        "pc": ("🖥 ПК", GUIDE_PC_VIDEO, GUIDE_PC_URL),
    }
    item = mapping.get(platform)
    if not item:
        await cb.answer("Платформа не найдена", show_alert=True)
        return

    title, video_src, fallback_url = item
    await cb.answer()

    if video_src:
        await cb.message.answer_video(
            video=video_src,
            caption=f"{title} — видео инструкция",
        )
    else:
        await cb.message.answer(
            f"{title} — видео пока не загружено.\n\nОткройте инструкцию: {fallback_url}"
        )


@router.callback_query(F.data == "support")
async def show_support(cb: CallbackQuery):
    support_url = f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"
    text = (
        f'{tg(E.HELP, "💬")} <b>Поддержка JetVPN</b>\n\n'
        "Если возникли вопросы с подключением или оплатой,\n"
        "напишите в поддержку:\n"
        f"{escape(SUPPORT_USERNAME)}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{SUPPORT_USERNAME}", url=support_url, icon_custom_emoji_id=E.SUPPORT_BOT)],
            row_back_main(),
        ]
    )
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML", photo_mode="support")
    await cb.answer()


@router.callback_query(F.data == "about")
async def show_about(cb: CallbackQuery):
    text = (
        f'{tg(E.FORME, "ℹ️")} <b>О нас</b>\n\n'
        "JetVPN — сервис для стабильного и удобного подключения.\n"
        "Мы постоянно улучшаем качество и поддержку пользователей."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Политика конфиденциальности", url=PRIVACY_POLICY_URL, icon_custom_emoji_id=E.DOC)],
            [InlineKeyboardButton(text="Пользовательское соглашение", url=TERMS_URL, icon_custom_emoji_id=E.DOC)],
            [InlineKeyboardButton(text="Контактная информация", url=CONTACT_INFO_URL, icon_custom_emoji_id=E.DOC)],
            row_back_main(),
        ]
    )
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML", photo_mode="about")
    await cb.answer()
