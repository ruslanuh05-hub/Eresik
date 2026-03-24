"""Команды /start и главное меню."""
import logging
from html import escape

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)

from database import get_or_create_user
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
)
from handlers.keyboards_common import markup_back_main_only, row_back_main
from handlers.ui_nav import apply_screen_from_callback

logger = logging.getLogger("jvpn-bot.start")

router = Router()


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
                    icon_custom_emoji_id=E.HELP,
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
                    text="Мои подписки 🎉",
                    callback_data="my_subscriptions",
                    icon_custom_emoji_id=E.PARTY,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Купить подписку 🎁",
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
            row_back_main(),
        ]
    )


def _welcome_text() -> str:
    return (
        f'{tg(E.HEART, "💜")} <b>Добро пожаловать в JetVPN!</b>\n\n'
        f'Выберите действие {tg(E.ARROW_DOWN, "⬇️")}'
    )


async def _send_welcome(msg: Message) -> None:
    """Приветствие: снимаем reply-клавиатуру, одно сообщение с inline-меню (+ фото в caption при наличии)."""
    await _strip_reply_keyboard(msg.bot, msg.chat.id)
    text = _welcome_text()
    kb = main_menu_inline()
    if WELCOME_IMAGE.exists():
        photo = FSInputFile(WELCOME_IMAGE)
        await msg.answer_photo(
            photo,
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    else:
        await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


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
        "Приглашайте друзей и получайте бонусы.\n\n"
        f"Ваш реферальный код: <code>{escape(code)}</code>\n"
        f"Ваша ссылка: <code>{escape(invite_link)}</code>\n\n"
        "Отправьте ссылку другу – и получите награду после его первой оплаты."
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
                    text="⚡️ Android",
                    callback_data="instruction:android",
                    icon_custom_emoji_id=E.MOLNY,
                ),
                InlineKeyboardButton(
                    text="⚡️ iOS",
                    callback_data="instruction:ios",
                    icon_custom_emoji_id=E.MOLNY,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚡️ Android TV",
                    callback_data="instruction:android_tv",
                    icon_custom_emoji_id=E.MOLNY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡️ ПК",
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
            [InlineKeyboardButton(text="✉️ Написать в поддержку", url=support_url)],
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
            [InlineKeyboardButton(text="🔒 Политика конфиденциальности", url=PRIVACY_POLICY_URL)],
            [InlineKeyboardButton(text="📄 Пользовательское соглашение", url=TERMS_URL)],
            [InlineKeyboardButton(text="📇 Контактная информация", url=CONTACT_INFO_URL)],
            row_back_main(),
        ]
    )
    await _safe_edit_message(cb, text, reply_markup=kb, parse_mode="HTML", photo_mode="about")
    await cb.answer()
