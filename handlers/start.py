"""Команды /start и главное меню."""
from html import escape

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart

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
)

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


def main_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Подключиться", callback_data="connect_menu")],
            [
                InlineKeyboardButton(
                    text="Профиль",
                    callback_data="cabinet",
                    icon_custom_emoji_id=E.USER_HEADER,
                ),
                InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
            ],
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="instruction")],
            [
                InlineKeyboardButton(text="💬 Поддержка", callback_data="support"),
                InlineKeyboardButton(text="ℹ️ О нас", callback_data="about"),
            ],
        ]
    )


def _welcome_text() -> str:
    return (
        f'{tg(E.HEART, "❤️")} <b>Добро пожаловать в JetVPN!</b>\n\n'
        f'Выберите нужное действие в меню ниже {tg(E.ARROW_DOWN, "⬇️")}'
    )


@router.message(CommandStart())
async def cmd_start(msg: Message):
    await get_or_create_user(msg.from_user.id, msg.from_user.username)
    text = _welcome_text()
    kb = main_keyboard()
    if WELCOME_IMAGE.exists():
        photo = FSInputFile(WELCOME_IMAGE)
        await msg.answer_photo(photo, caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.callback_query(F.data == "main_menu")
async def back_to_main(cb: CallbackQuery):
    text = _welcome_text()
    kb = main_keyboard()
    if WELCOME_IMAGE.exists():
        await cb.message.delete()
        photo = FSInputFile(WELCOME_IMAGE)
        await cb.message.answer_photo(photo, caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        try:
            await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            await cb.message.delete()
            await cb.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()


def connect_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Мои подписки", callback_data="my_subscriptions")],
            [InlineKeyboardButton(text="📦 Купить подписку", callback_data="buy_sub")],
            [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="topup")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
        ]
    )


@router.callback_query(F.data == "connect_menu")
async def show_connect_menu(cb: CallbackQuery):
    """Окно 'Подключиться' с быстрыми действиями."""
    text = (
        "🚀 <b>Подключиться</b>\n\n"
        "Выберите действие:"
    )
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
        "👥 <b>Реферальная система</b>\n\n"
        "Приглашайте друзей и получайте бонусы.\n\n"
        f"Ваш реферальный код: <code>{escape(code)}</code>\n"
        f"Ваша ссылка: <code>{escape(invite_link)}</code>\n\n"
        "Отправьте ссылку другу и получите награду после его первой оплаты."
    )
    kb = main_keyboard()
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "instruction")
async def show_instruction(cb: CallbackQuery):
    """Инструкция: выбор платформы, после чего бот присылает видео."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    text = (
        "📖 <b>Инструкция по подключению</b>\n\n"
        "Выберите платформу, и я отправлю видео-инструкцию:"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Android", callback_data="instruction:android")],
            [InlineKeyboardButton(text="🍏 iOS", callback_data="instruction:ios")],
            [InlineKeyboardButton(text="📺 Android TV", callback_data="instruction:android_tv")],
            [InlineKeyboardButton(text="🖥 ПК", callback_data="instruction:pc")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
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
        # Можно передать file_id Telegram или прямую ссылку на mp4.
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
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
        ]
    )
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "about")
async def show_about(cb: CallbackQuery):
    """О нас + кнопки с текстом политики и соглашения в чате."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    text = (
        "ℹ️ <b>О нас</b>\n\n"
        "JetVPN — сервис для стабильного и удобного подключения.\n"
        "Мы постоянно улучшаем качество и поддержку пользователей."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔒 Политика конфиденциальности", callback_data="about:privacy")],
            [InlineKeyboardButton(text="📄 Пользовательское соглашение", callback_data="about:terms")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
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

