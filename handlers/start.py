"""Команды /start и главное меню."""
import logging
from html import escape

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database import get_or_create_user
from tgemoji import E, tg
from config import (
    WELCOME_IMAGE,
    SUPPORT_USERNAME,
    GUIDE_ANDROID_URL,
    GUIDE_IOS_URL,
    GUIDE_ANDROID_TV_URL,
    GUIDE_PC_URL,
    GUIDE_ANDROID_VIDEO,
    GUIDE_IOS_VIDEO,
    GUIDE_ANDROID_TV_VIDEO,
    GUIDE_PC_VIDEO,
    ADMIN_IDS,
)
from handlers.reply_menu import ReplyMenu, reply_main_keyboard
from handlers.cabinet import _deliver_cabinet, cabinet_keyboard, generate_subscription_image
from handlers.topup import topup_keyboard

logger = logging.getLogger("jvpn-bot.start")

router = Router()


async def _safe_edit_message(cb: CallbackQuery, text: str, reply_markup=None, parse_mode: str = "HTML"):
    """Безопасно редактировать текст/подпись сообщения из callback."""
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


def _back_main_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]]
    )


def connect_keyboard() -> InlineKeyboardMarkup:
    """Экран «Подписка»: без пополнения (оно на reply-клавиатуре)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Мои подписки", callback_data="my_subscriptions")],
            [InlineKeyboardButton(text="📦 Купить подписку", callback_data="buy_sub")],
            [
                InlineKeyboardButton(
                    text="Рефералы",
                    callback_data="referrals",
                    icon_custom_emoji_id=E.REFERRAL,
                ),
            ],
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="instruction")],
        ]
    )


def _welcome_text() -> str:
    return (
        f'{tg(E.HEART, "💜")} <b>Добро пожаловать в JetVPN!</b>\n\n'
        f'Выберите нужное действие в меню ниже {tg(E.ARROW_DOWN, "⬇️")}'
    )


async def _send_welcome(msg: Message) -> None:
    """Приветствие без inline; reply-клавиатура. Фото и текст — одно сообщение (caption), если есть WELCOME_IMAGE."""
    text = _welcome_text()
    rkb = reply_main_keyboard()
    if WELCOME_IMAGE.exists():
        photo = FSInputFile(WELCOME_IMAGE)
        await msg.answer_photo(
            photo,
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=rkb,
        )
    else:
        await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=rkb)


@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await get_or_create_user(msg.from_user.id, msg.from_user.username)
    await _send_welcome(msg)


@router.callback_query(F.data == "main_menu")
async def back_to_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.answer()
    text = _welcome_text()
    rkb = reply_main_keyboard()
    uid = cb.from_user.id
    try:
        if cb.message:
            try:
                await cb.message.delete()
            except Exception:
                pass
    except Exception:
        logger.debug("back_to_main: delete old message skipped")
    try:
        if WELCOME_IMAGE.exists():
            photo = FSInputFile(WELCOME_IMAGE)
            await cb.bot.send_photo(
                uid,
                photo,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=rkb,
            )
        else:
            await cb.bot.send_message(uid, text, parse_mode=ParseMode.HTML, reply_markup=rkb)
    except Exception:
        logger.exception("back_to_main: send welcome")
        try:
            await cb.bot.send_message(uid, text, parse_mode=ParseMode.HTML, reply_markup=rkb)
        except Exception:
            pass


@router.message(F.text == ReplyMenu.SUBSCRIPTION, StateFilter(default_state))
async def menu_reply_subscription(msg: Message):
    text = "📦 <b>Подписка</b>\n\nВыберите действие:"
    await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=connect_keyboard())


@router.message(F.text == ReplyMenu.TOPUP, StateFilter(default_state))
async def menu_reply_topup(msg: Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(msg.from_user.id)
    try:
        balance = float(user.get("balance") or 0)
    except (TypeError, ValueError):
        balance = 0.0
    is_admin = msg.from_user.id in ADMIN_IDS
    text = (
        f"💳 <b>Пополнение баланса</b>\n\n"
        f"Текущий баланс: <b>{balance:.2f} ₽</b>\n\n"
        "Выберите сумму или введите свою (минимум 50 ₽):"
    )
    await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=topup_keyboard(is_admin))


@router.message(F.text == ReplyMenu.ABOUT, StateFilter(default_state))
async def menu_reply_about(msg: Message):
    text = (
        "ℹ️ <b>О нас</b>\n\n"
        "JetVPN — сервис для стабильного и удобного подключения.\n"
        "Мы постоянно улучшаем качество и поддержку пользователей."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔒 Политика конфиденциальности", callback_data="about:privacy")],
            [InlineKeyboardButton(text="📄 Пользовательское соглашение", callback_data="about:terms")],
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")],
        ]
    )
    await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.message(F.text == ReplyMenu.PROFILE, StateFilter(default_state))
async def menu_reply_profile(msg: Message):
    user = await get_or_create_user(msg.from_user.id)
    kb = cabinet_keyboard()
    img_bytes: bytes | None = None
    try:
        img_bytes = generate_subscription_image(
            user.get("subscription_expires_at"),
            user.get("nickname") or msg.from_user.username or "",
        )
    except Exception:
        logger.exception("menu_reply_profile: image generation")
    try:
        await _deliver_cabinet(
            msg.bot,
            msg.chat.id,
            msg.from_user.id,
            reply_markup=kb,
            photo_bytes=img_bytes,
        )
    except Exception:
        logger.exception("menu_reply_profile: deliver")
        await msg.answer("Не удалось открыть профиль. Попробуйте /my")


@router.message(F.text == ReplyMenu.HELP, StateFilter(default_state))
async def menu_reply_support(msg: Message):
    support_url = f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"
    text = (
        "💬 <b>Поддержка JetVPN</b>\n\n"
        "Если возникли вопросы с подключением или оплатой,\n"
        "напишите в поддержку:\n"
        f"{escape(SUPPORT_USERNAME)}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Написать в поддержку", url=support_url)],
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")],
        ]
    )
    await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.callback_query(F.data == "connect_menu")
async def show_connect_menu(cb: CallbackQuery):
    """Тот же экран, что и reply-кнопка «Подписка»."""
    text = "📦 <b>Подписка</b>\n\nВыберите действие:"
    kb = connect_keyboard()
    try:
        if cb.message.caption is not None:
            await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception:
        await cb.message.delete()
        await cb.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "referrals")
async def show_referrals(cb: CallbackQuery):
    """Реферальная система (базовая версия)."""
    await get_or_create_user(cb.from_user.id, cb.from_user.username)
    code = f"ref_{cb.from_user.id}"
    bot_username = (await cb.bot.me()).username
    invite_link = f"https://t.me/{bot_username}?start={code}" if bot_username else "Ссылка недоступна"
    text = (
        f'{tg(E.REFERRAL, "👥")} <b>Реферальная система</b>\n\n'
        "Приглашайте друзей и получайте бонусы.\n\n"
        f"Ваш реферальный код: <code>{escape(code)}</code>\n"
        f"Ваша ссылка: <code>{escape(invite_link)}</code>\n\n"
        "Отправьте ссылку другу – и получите награду после его первой оплаты."
    )
    await _safe_edit_message(cb, text, reply_markup=_back_main_inline(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "instruction")
async def show_instruction(cb: CallbackQuery):
    """Инструкция: выбор платформы, после чего бот присылает видео."""
    text = (
        f'{tg(E.INSTRUCTION_BOOKMARK, "🏷️")} <b>Инструкция по подключению</b>\n\n'
        "Выберите платформу, и я отправлю видео-инструкцию:"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Android",
                    callback_data="instruction:android",
                    icon_custom_emoji_id=E.ANDROID_ROBOT,
                ),
                InlineKeyboardButton(
                    text="iOS",
                    callback_data="instruction:ios",
                    icon_custom_emoji_id=E.IOS_APPLE,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Android TV",
                    callback_data="instruction:android_tv",
                    icon_custom_emoji_id=E.TV,
                )
            ],
            [
                InlineKeyboardButton(
                    text="ПК",
                    callback_data="instruction:pc",
                    icon_custom_emoji_id=E.PC_LAPTOP,
                )
            ],
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")],
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
    """Поддержка — аккуратный блок с username."""
    support_url = f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"
    text = (
        "💬 <b>Поддержка JetVPN</b>\n\n"
        "Если возникли вопросы с подключением или оплатой,\n"
        "напишите в поддержку:\n"
        f"{escape(SUPPORT_USERNAME)}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Написать в поддержку", url=support_url)],
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")],
        ]
    )
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "about")
async def show_about(cb: CallbackQuery):
    """О нас + кнопки с текстом политики и соглашения в чате."""
    text = (
        "ℹ️ <b>О нас</b>\n\n"
        "JetVPN — сервис для стабильного и удобного подключения.\n"
        "Мы постоянно улучшаем качество и поддержку пользователей."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔒 Политика конфиденциальности", callback_data="about:privacy")],
            [InlineKeyboardButton(text="📄 Пользовательское соглашение", callback_data="about:terms")],
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")],
        ]
    )
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "about:privacy")
async def send_privacy_policy(cb: CallbackQuery):
    from legal_texts import privacy_policy_text

    await cb.message.answer(privacy_policy_text(), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data == "about:terms")
async def send_terms_of_use(cb: CallbackQuery):
    from legal_texts import terms_of_use_text

    await cb.message.answer(terms_of_use_text(), parse_mode=ParseMode.HTML)
    await cb.answer()
