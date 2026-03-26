"""Админ-панель (UI/навигация + рабочие секции под ваш макет)."""

import asyncio
from datetime import datetime
import re
import secrets

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from handlers.admin import AdminFilter
from config import ADMIN_IDS
from database import (
    add_gift_subscription_days,
    block_subscription,
    get_or_create_user,
    get_user_by_telegram_id,
    get_user_by_username,
    list_users,
    count_users,
    list_payments,
    get_payment_by_id,
    list_servers,
    list_admin_keys,
    get_admin_stats,
    reset_subscription_token,
    update_payment_status_by_id,
    update_user,
    list_user_ids,
)

router = Router()


def back_btn(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data),
            ]
        ]
    )


def admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔧 Админ-панель", callback_data="adminpanel:home"),
            ],
            [
                InlineKeyboardButton(text="👤 Пользователи", callback_data="adminpanel:users"),
                InlineKeyboardButton(text="💳 Платежи", callback_data="adminpanel:payments"),
            ],
            [
                InlineKeyboardButton(text="🌍 Серверы", callback_data="adminpanel:servers"),
                InlineKeyboardButton(text="🔑 Ключи", callback_data="adminpanel:keys"),
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="adminpanel:stats"),
                InlineKeyboardButton(text="📣 Рассылка", callback_data="adminpanel:broadcasts"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="adminpanel:settings"),
                InlineKeyboardButton(text="🛡 Безопасность", callback_data="adminpanel:security"),
            ],
            [
                InlineKeyboardButton(text="💬 Поддержка", callback_data="adminpanel:support"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="adminpanel:close"),
            ],
        ]
    )


def admin_section_keyboard(section: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="adminpanel:home"),
            ]
        ]
    )


def _section_text(section: str) -> str:
    mapping = {
        "users": "👤 Пользователи\n\nЗдесь будет поиск, список, выдача доступа и блокировка.",
        "payments": "💳 Платежи\n\nЗдесь будет просмотр платежей и статусы (pending/completed).",
        "servers": "🌍 Серверы\n\nЗдесь будет список серверов и управление.",
        "keys": "🔑 Ключи\n\nЗдесь будет поиск/создание/сброс ключей.",
        "stats": "📊 Статистика\n\nЗдесь будет агрегированная статистика по пользователям/доходу/серверам.",
        "broadcasts": "📣 Рассылка\n\nЗдесь будет создание и история рассылок.",
        "settings": "⚙️ Настройки\n\nЗдесь будут цены/пробный период/тексты и т.д.",
        "security": "🛡 Безопасность\n\nЗдесь будут лимиты устройств/IP и подозрительная активность.",
        "support": "💬 Поддержка\n\nЗдесь можно будет открыть поддержку или настройки контакта.",
    }
    return mapping.get(section, "Админ-панель")


@router.message(Command("adminpanel"))
async def cmd_adminpanel(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Доступ запрещен.")
        return
    await state.clear()
    await msg.answer(_section_text("admin"), reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "adminpanel:home", AdminFilter())
async def admin_home(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("🔧 Админ-панель", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "adminpanel:close", AdminFilter())
async def admin_close(cb: CallbackQuery):
    await cb.answer()
    try:
        await cb.message.delete()
    except Exception:
        pass


@router.callback_query(
    F.data.startswith("adminpanel:"), AdminFilter()
)
async def admin_section_router(cb: CallbackQuery):
    """Диспетчер по разделам."""
    await cb.answer()
    section = str(cb.data).split(":", 1)[1]
    if section == "home" or section == "close":
        return

    if section == "users":
        user = await list_users(limit=1)
        # Не используем `user` — просто гарантируем, что БД доступна перед отрисовкой меню.
        await cb.message.edit_text(
            _section_text("users"),
            reply_markup=admin_users_menu_keyboard(),
        )
        return

    if section == "settings":
        await cb.message.edit_text(
            _section_text("settings"),
            reply_markup=admin_settings_keyboard(),
        )
        return

    if section == "payments":
        await cb.message.edit_text(
            _section_text("payments"),
            reply_markup=admin_payments_menu_keyboard(),
        )
        return

    if section == "servers":
        servers = await list_servers(limit=20)
        lines = ["🌍 Серверы\n"]
        if not servers:
            lines.append("Пока нет серверов в БД.")
        else:
            for s in servers:
                sid = s.get("id")
                name = s.get("name") or "—"
                cc = s.get("country_code") or "—"
                online = s.get("is_online")
                badge = "🟢" if online in (True, 1, "1") else "⚪️"
                load = s.get("load_value", 0)
                lines.append(f"{badge} ID {sid}: {name} ({cc}) — load:{load}")
        await cb.message.edit_text(
            "\n".join(lines),
            reply_markup=admin_section_keyboard("servers"),
        )
        return

    if section == "keys":
        keys = await list_admin_keys(limit=20)
        lines = ["🔑 Ключи\n"]
        if not keys:
            lines.append("Пока нет ключей в БД.")
        else:
            for k in keys:
                kid = k.get("id")
                owner = k.get("owner_telegram_id") or "—"
                expires = _format_ts(k.get("expires_at"))
                traffic_used = k.get("traffic_used_bytes", 0)
                lines.append(f"• ID {kid}: owner:{owner} expires:{expires} used:{traffic_used}B")
        await cb.message.edit_text(
            "\n".join(lines),
            reply_markup=admin_section_keyboard("keys"),
        )
        return

    if section == "stats":
        stats = await get_admin_stats()
        text = (
            "📊 Статистика\n\n"
            f"Пользователей: {stats.get('total_users', 0)}\n"
            f"Активных: {stats.get('active_users', 0)}\n"
            f"Выручка (completed): {stats.get('revenue_completed', 0):.2f} ₽\n"
            f"Выручка (pending): {stats.get('revenue_pending', 0):.2f} ₽\n"
            f"Серверы online: {stats.get('servers_online', 0)}"
        )
        await cb.message.edit_text(text, reply_markup=admin_section_keyboard("stats"))
        return

    if section == "broadcasts":
        total = await count_users()
        await cb.message.edit_text(
            _section_text("broadcasts") + f"\n\nВсего пользователей: <b>{total}</b>",
            reply_markup=admin_broadcast_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    await cb.message.edit_text(_section_text(section), reply_markup=admin_section_keyboard(section))


def admin_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Изменить цену за 1 день", callback_data="admin:price"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="adminpanel:home"),
            ],
        ]
    )


def admin_payments_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟦 Все", callback_data="adminpayments:filter:all"),
                InlineKeyboardButton(text="🟨 pending", callback_data="adminpayments:filter:pending"),
            ],
            [
                InlineKeyboardButton(text="🟩 completed", callback_data="adminpayments:filter:completed"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="adminpanel:home"),
            ],
        ]
    )


def admin_payments_list_text(payments: list[dict]) -> str:
    if not payments:
        return "Платежи не найдены."
    lines = ["📋 Платежи (последние):"]
    for p in payments[:10]:
        pid = p.get("id")
        status = p.get("status")
        amount = p.get("amount", 0)
        tg_id = p.get("telegram_id")
        lines.append(f"• ID {pid}: {status} — {amount} ₽ (tg:{tg_id})")
    lines.append("\nДля действий откройте детальную карточку по `ID`.")
    return "\n".join(lines)


def admin_payments_build_ids_keyboard(rows: list[dict], back_callback: str) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    for p in rows[:8]:
        pid = p.get("id")
        if pid is None:
            continue
        buttons.append(
            InlineKeyboardButton(
                text=f"ID {pid}",
                callback_data=f"adminpayments:detail:{pid}",
            )
        )

    inline_rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), 4):
        inline_rows.append(buttons[i : i + 4])

    if not inline_rows:
        inline_rows = [[InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)]]
    else:
        inline_rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)])

    return InlineKeyboardMarkup(inline_keyboard=inline_rows)


@router.callback_query(F.data == "adminpayments:filter:all", AdminFilter())
async def admin_payments_filter_all(cb: CallbackQuery):
    await cb.answer()
    rows = await list_payments(limit=30, status=None)
    text = admin_payments_list_text(rows)
    kb = admin_payments_build_ids_keyboard(rows, back_callback="adminpanel:payments")
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "adminpayments:filter:pending", AdminFilter())
async def admin_payments_filter_pending(cb: CallbackQuery):
    await cb.answer()
    rows = await list_payments(limit=30, status="pending")
    text = admin_payments_list_text(rows)
    kb = admin_payments_build_ids_keyboard(rows, back_callback="adminpanel:payments")
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "adminpayments:filter:completed", AdminFilter())
async def admin_payments_filter_completed(cb: CallbackQuery):
    await cb.answer()
    rows = await list_payments(limit=30, status="completed")
    text = admin_payments_list_text(rows)
    kb = admin_payments_build_ids_keyboard(rows, back_callback="adminpanel:payments")
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("adminpayments:detail:"), AdminFilter())
async def admin_payment_detail(cb: CallbackQuery):
    await cb.answer()
    try:
        pid = int(str(cb.data).split(":", 2)[2])
    except Exception:
        await cb.message.edit_text("Ошибка ID.", reply_markup=admin_payments_menu_keyboard())
        return

    payment = await get_payment_by_id(pid)
    if not payment:
        await cb.message.edit_text("Платеж не найден.", reply_markup=admin_payments_menu_keyboard())
        return

    status = payment.get("status")
    tg_id = payment.get("telegram_id")
    amount = payment.get("amount", 0)
    order_id = payment.get("order_id") or "—"
    freekassa_order_id = payment.get("freekassa_order_id") or "—"

    text = (
        f"💳 Платеж\n\n"
        f"ID: <code>{pid}</code>\n"
        f"Telegram ID: <code>{tg_id}</code>\n"
        f"Сумма: <b>{amount} ₽</b>\n"
        f"Статус: <b>{status}</b>\n"
        f"order_id: <code>{order_id}</code>\n"
        f"freekassa_order_id: <code>{freekassa_order_id}</code>"
    )

    kb_rows = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adminpanel:payments")],
    ]
    if status != "completed":
        kb_rows.insert(
            0,
            [InlineKeyboardButton(text="✅ Пометить как completed", callback_data=f"adminpayments:confirm:completed:{pid}")],
        )

    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data.startswith("adminpayments:confirm:"), AdminFilter())
async def admin_payment_confirm(cb: CallbackQuery):
    await cb.answer()
    parts = str(cb.data).split(":")
    # adminpayments:confirm:<status>:<pid>
    if len(parts) < 4:
        await cb.message.edit_text("Ошибка подтверждения.", reply_markup=admin_payments_menu_keyboard())
        return
    new_status = parts[2]
    pid = int(parts[3])

    await cb.message.edit_text(
        "Вы уверены?",
        reply_markup=admin_confirm_keyboard(
            yes_callback_data=f"adminpayments:do:{new_status}:{pid}",
            no_callback_data=f"adminpayments:detail:{pid}",
        ),
    )


@router.callback_query(F.data.startswith("adminpayments:do:"), AdminFilter())
async def admin_payment_do(cb: CallbackQuery):
    await cb.answer()
    parts = str(cb.data).split(":")
    if len(parts) < 4:
        await cb.message.edit_text("Ошибка выполнения.", reply_markup=admin_payments_menu_keyboard())
        return
    new_status = parts[2]
    pid = int(parts[3])

    await update_payment_status_by_id(pid, new_status)
    payment = await get_payment_by_id(pid)
    if not payment:
        await cb.message.edit_text("Готово, но платеж не найден.", reply_markup=admin_payments_menu_keyboard())
        return

    status = payment.get("status")
    tg_id = payment.get("telegram_id")
    amount = payment.get("amount", 0)
    order_id = payment.get("order_id") or "—"
    freekassa_order_id = payment.get("freekassa_order_id") or "—"

    text = (
        f"💳 Платеж\n\n"
        f"ID: <code>{pid}</code>\n"
        f"Telegram ID: <code>{tg_id}</code>\n"
        f"Сумма: <b>{amount} ₽</b>\n"
        f"Статус: <b>{status}</b>\n"
        f"order_id: <code>{order_id}</code>\n"
        f"freekassa_order_id: <code>{freekassa_order_id}</code>"
    )
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="adminpanel:payments")],
            ]
        ),
    )


class AdminUsersStates(StatesGroup):
    waiting_search_input = State()
    waiting_message_text = State()
    waiting_add_manual_id = State()


def admin_users_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="adminusers:search"),
            ],
            [
                InlineKeyboardButton(text="📋 Список пользователей", callback_data="adminusers:list:50"),
            ],
            [
                InlineKeyboardButton(text="➕ Добавить вручную", callback_data="adminusers:addmanual"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="adminpanel:home"),
            ],
        ]
    )


def _format_ts(ts: int | None) -> str:
    if not ts:
        return "—"
    try:
        dt = datetime.fromtimestamp(int(ts))
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return "—"


def _is_active_subscription(expires_at: int | None) -> bool:
    if not expires_at:
        return False
    # expires_at в БД хранится как unixtime в секундах; сравнение по текущему времени.
    return int(expires_at) > int(datetime.now().timestamp())


def admin_user_detail_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    uid = int(telegram_id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Выдать доступ (30д)", callback_data=f"adminusers:confirm:give:30:{uid}"),
            ],
            [
                InlineKeyboardButton(text="⏳ Продлить (30д)", callback_data=f"adminusers:confirm:extend:30:{uid}"),
            ],
            [
                InlineKeyboardButton(text="⛔️ Блокировать", callback_data=f"adminusers:confirm:block:{uid}"),
            ],
            [
                InlineKeyboardButton(text="🔑 Сбросить ключ", callback_data=f"adminusers:confirm:resetkey:{uid}"),
            ],
            [
                InlineKeyboardButton(text="✉️ Написать", callback_data=f"adminusers:message:{uid}"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="adminusers:back"),
            ],
        ]
    )


def admin_confirm_keyboard(yes_callback_data: str, no_callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data=yes_callback_data),
                InlineKeyboardButton(text="Нет", callback_data=no_callback_data),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=no_callback_data),
            ],
        ]
    )


def admin_user_detail_text(user: dict) -> tuple[str, InlineKeyboardMarkup]:
    uid = int(user["telegram_id"])
    created = _format_ts(user.get("created_at"))
    username = user.get("username") or ""
    nickname = user.get("nickname") or ""
    display_name = f"@{username}" if username else nickname
    expires_at = user.get("subscription_expires_at")

    text = (
        f"👤 Пользователь: {display_name}\n"
        f"ID: <code>{uid}</code>\n"
        f"Создан: {created}\n"
        f"Баланс: {user.get('balance', 0)} ₽\n"
        f"Подписка: {'АКТИВНА' if _is_active_subscription(expires_at) else 'НЕАКТИВНА'}\n"
        f"Действует до: {_format_ts(expires_at)}"
    )
    return text, admin_user_detail_keyboard(uid)


@router.callback_query(F.data == "adminusers:search", AdminFilter())
async def admin_users_search(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminUsersStates.waiting_search_input)
    await state.update_data(last_admin_view="adminusers:menu")
    await cb.message.edit_text(
        "🔍 Введите `ID` пользователя или `@username`.\n\nПример:\n123456789\n@user_name",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="adminusers:back")]]
        ),
    )


@router.callback_query(F.data == "adminusers:list:50", AdminFilter())
async def admin_users_list_50(cb: CallbackQuery):
    await cb.answer()
    rows = await list_users(limit=50)
    if not rows:
        await cb.message.edit_text("Список пользователей пуст.", reply_markup=admin_users_menu_keyboard())
        return

    # Поскольку Telegram меню должно быть компактным, показываем топ-15.
    top = rows[:15]
    lines = ["📋 Список пользователей (первые 15):\n"]
    for r in top:
        tg_id = r.get("telegram_id")
        username = r.get("username") or ""
        nickname = r.get("nickname") or ""
        active = _is_active_subscription(r.get("subscription_expires_at"))
        badge = "🟢" if active else "⚪️"
        u = f"@{username}" if username else nickname
        lines.append(f"{badge} {tg_id} — {u}")
    lines.append("\nВыберите пользователя через поиск (в этом макете пока нет пагинации).")

    await cb.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_users_menu_keyboard(),
    )


@router.callback_query(F.data == "adminusers:addmanual", AdminFilter())
async def admin_users_add_manual(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminUsersStates.waiting_add_manual_id)
    await cb.message.edit_text(
        "➕ Введите `telegram_id` пользователя (число), которого нужно добавить в БД.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="adminusers:back")]]
        ),
    )


@router.message(AdminUsersStates.waiting_add_manual_id, AdminFilter())
async def admin_users_add_manual_id(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if not text.isdigit():
        await msg.answer("ID должен быть числом. Попробуйте ещё раз.")
        return
    tg_id = int(text)
    await get_or_create_user(tg_id, None)
    await state.clear()
    await msg.answer("Пользователь добавлен/найден в БД.", reply_markup=admin_users_menu_keyboard())


@router.message(AdminUsersStates.waiting_search_input, AdminFilter())
async def admin_users_search_input(msg: Message, state: FSMContext):
    q = (msg.text or "").strip()
    await state.clear()

    target = None
    if q.isdigit():
        target = await get_user_by_telegram_id(int(q))
    else:
        # ожидаем `@username` или голое username
        target = await get_user_by_username(q)

    if not target:
        await msg.answer("Пользователь не найден. Попробуйте другой ID/@username.", reply_markup=admin_users_menu_keyboard())
        return

    uid = int(target["telegram_id"])
    created = _format_ts(target.get("created_at"))
    username = target.get("username") or ""
    nickname = target.get("nickname") or ""
    display_name = f"@{username}" if username else nickname
    expires_at = target.get("subscription_expires_at")
    is_active = _is_active_subscription(expires_at)

    text = (
        f"👤 Пользователь: {display_name}\n"
        f"ID: <code>{uid}</code>\n"
        f"Создан: {created}\n"
        f"Баланс: {target.get('balance', 0)} ₽\n"
        f"Подписка: {'АКТИВНА' if is_active else 'НЕАКТИВНА'}\n"
        f"Действует до: {_format_ts(expires_at)}"
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=admin_user_detail_keyboard(uid))


@router.callback_query(F.data == "adminusers:back", AdminFilter())
async def admin_users_back(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(_section_text("users"), reply_markup=admin_users_menu_keyboard())


@router.callback_query(F.data.startswith("adminusers:message:"), AdminFilter())
async def admin_users_message_start(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    uid = int(str(cb.data).split(":", 2)[2])
    await state.set_state(AdminUsersStates.waiting_message_text)
    await state.update_data(target_uid=uid)
    await cb.message.edit_text(
        "✉️ Введите текст сообщения для пользователя.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="adminusers:back")]]
        ),
    )


@router.message(AdminUsersStates.waiting_message_text, AdminFilter())
async def admin_users_message_send(msg: Message, state: FSMContext):
    data = await state.get_data()
    uid = int(data["target_uid"])
    text = (msg.text or "").strip()
    await state.clear()

    # Отправляем пользователю. Если пользователь не стартовал бота, Telegram может вернуть ошибку.
    try:
        await msg.bot.send_message(uid, text)
        await msg.answer("Сообщение отправлено.", reply_markup=admin_users_menu_keyboard())
    except Exception as e:
        await msg.answer(f"Не удалось отправить: {e}", reply_markup=admin_users_menu_keyboard())


def _parse_confirm_payload(data: str) -> tuple[str, int, str | None]:
    # adminusers:confirm:<action>:<days?>:<uid?>
    parts = str(data).split(":")
    # [0]=adminusers [1]=confirm [2]=action [3]=days? [4]=uid
    if len(parts) < 4:
        raise ValueError("bad confirm payload")
    action = parts[2]
    if action in {"block", "resetkey"}:
        uid = int(parts[3])
        return action, uid, None
    # give/extend with days
    days = parts[3]
    uid = int(parts[4])
    return action, uid, days


@router.callback_query(F.data.startswith("adminusers:confirm:"), AdminFilter())
async def admin_users_confirm_handler(cb: CallbackQuery):
    await cb.answer()
    payload = str(cb.data)
    # We show confirm UI when first clicking; next click executes operation.
    # To implement both without FSM, we use two-step callback_data:
    #  - first click: adminusers:confirm:<action>:... triggers confirm message
    #  - second click: adminusers:do:<action>:... executes
    if ":do:" in payload:
        return

    action, uid, days = _parse_confirm_payload(payload)
    yes = f"adminusers:do:{action}:{days or ''}:{uid}"
    # no returns back to detail if possible
    no = f"adminusers:show:{uid}"
    if action in {"block", "resetkey"}:
        yes = f"adminusers:do:{action}:{uid}"

    await cb.message.edit_text(
        "Вы уверены?",
        reply_markup=admin_confirm_keyboard(yes, no),
    )


@router.callback_query(F.data.startswith("adminusers:do:"), AdminFilter())
async def admin_users_do_handler(cb: CallbackQuery):
    await cb.answer()
    data = str(cb.data)
    parts = data.split(":")
    # adminusers:do:<action>:...:
    action = parts[2]
    try:
        if action in {"block", "resetkey"}:
            uid = int(parts[3])
        else:
            # do:give/extend:<days>:<uid>
            uid = int(parts[-1])
            days = int(parts[3]) if len(parts) > 3 and parts[3] else 30
    except Exception:
        await cb.message.edit_text("Ошибка параметров команды.", reply_markup=admin_users_menu_keyboard())
        return

    try:
        if action == "give":
            # "Выдать доступ" -> бонусные дни без списания баланса
            await add_gift_subscription_days(uid, int(days), "d30")
        elif action == "extend":
            await add_gift_subscription_days(uid, int(days), "d30")
        elif action == "block":
            await block_subscription(uid)
        elif action == "resetkey":
            await reset_subscription_token(uid)
        else:
            await cb.message.edit_text("Неизвестное действие.", reply_markup=admin_users_menu_keyboard())
            return
    except Exception as e:
        await cb.message.edit_text(f"Ошибка выполнения: {e}", reply_markup=admin_users_menu_keyboard())
        return

    user = await get_user_by_telegram_id(uid)
    if not user:
        await cb.message.edit_text("Операция выполнена, но пользователь не найден в БД.", reply_markup=admin_users_menu_keyboard())
        return

    detail_text, detail_kb = admin_user_detail_text(user)
    await cb.message.edit_text(
        f"✅ Готово.\n\n{detail_text}",
        parse_mode="HTML",
        reply_markup=detail_kb,
    )


@router.callback_query(F.data.startswith("adminusers:show:"), AdminFilter())
async def admin_users_show(cb: CallbackQuery):
    await cb.answer()
    try:
        uid = int(str(cb.data).split(":", 2)[2])
    except Exception:
        await cb.message.edit_text("Ошибка параметров.", reply_markup=admin_users_menu_keyboard())
        return

    user = await get_user_by_telegram_id(uid)
    if not user:
        await cb.message.edit_text("Пользователь не найден в БД.", reply_markup=admin_users_menu_keyboard())
        return

    detail_text, detail_kb = admin_user_detail_text(user)
    await cb.message.edit_text(detail_text, parse_mode="HTML", reply_markup=detail_kb)


class AdminBroadcastStates(StatesGroup):
    waiting_photo_or_skip = State()
    waiting_buttons = State()
    waiting_text = State()


def admin_broadcast_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Новая рассылка", callback_data="adminbroadcast:new")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="adminpanel:home")],
        ]
    )


def admin_broadcast_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="adminbroadcast:cancel")],
        ]
    )


def _parse_button_labels(raw: str) -> list[str]:
    parts = re.split(r"[,\n]+", raw)
    labels = [p.strip() for p in parts if p.strip()]
    # Telegram: InlineKeyboardButton text up to 64 bytes, но на практике держим короче.
    return [l[:40] for l in labels]


def _build_broadcast_keyboard(broadcast_id: str, labels: list[str]) -> InlineKeyboardMarkup | None:
    if not labels:
        return None

    buttons = [
        InlineKeyboardButton(
            text=label,
            callback_data=f"adminbroadcast:btn:{broadcast_id}:{i}",
        )
        for i, label in enumerate(labels)
    ]

    # 2 колонки, чтобы оставаться в лимитах Telegram.
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "adminbroadcast:cancel", AdminFilter())
async def admin_broadcast_cancel(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    total = await count_users()
    await cb.message.edit_text(
        _section_text("broadcasts") + f"\n\nВсего пользователей: <b>{total}</b>",
        reply_markup=admin_broadcast_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adminbroadcast:new", AdminFilter())
async def admin_broadcast_new(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()

    broadcast_id = secrets.token_hex(4)  # 8 hex chars
    await state.set_state(AdminBroadcastStates.waiting_photo_or_skip)
    await state.update_data(
        broadcast_id=broadcast_id,
        photo_file_id=None,
        button_labels=[],
        message_text=None,
    )

    await cb.message.edit_text(
        "📣 <b>Новая рассылка</b>\n\n"
        "Пришлите фото для рассылки (можно без фото).\n"
        "Или напишите <b>«пропустить»</b> чтобы отправлять только текст.\n",
        reply_markup=admin_broadcast_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(AdminBroadcastStates.waiting_photo_or_skip, AdminFilter())
async def admin_broadcast_wait_photo(msg: Message, state: FSMContext):
    if msg.photo:
        # Берём самое большое по размеру фото из списка версий.
        photo_file_id = msg.photo[-1].file_id
        await state.update_data(photo_file_id=photo_file_id)
        await state.set_state(AdminBroadcastStates.waiting_buttons)
        await msg.answer(
            "Фото сохранено.\n\n"
            "Добавьте кнопки (без ссылок) — отправьте названия кнопок через запятую или новую строку.\n"
            "Например: `Кнопка 1\\nКнопка 2`.\n"
            "Чтобы без кнопок — напишите <b>«пропустить»</b>.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Готово", callback_data="adminbroadcast:buttons_done")],
                    [InlineKeyboardButton(text="⬅️ Отмена", callback_data="adminbroadcast:cancel")],
                ]
            ),
            parse_mode="HTML",
        )
        return

    text = (msg.text or "").strip().lower()
    if text in {"пропустить", "skip", "без фото", "без картинки"}:
        await state.update_data(photo_file_id=None)
        await state.set_state(AdminBroadcastStates.waiting_buttons)
        await msg.answer(
            "Ок, отправляем без фото.\n\n"
            "Добавьте кнопки (без ссылок) или напишите <b>«пропустить»</b> чтобы сразу перейти к тексту.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Готово", callback_data="adminbroadcast:buttons_done")],
                    [InlineKeyboardButton(text="⬅️ Отмена", callback_data="adminbroadcast:cancel")],
                ]
            ),
            parse_mode="HTML",
        )
        return

    await msg.answer("Нужно либо фото, либо текст «пропустить».", reply_markup=admin_broadcast_cancel_keyboard())


@router.message(AdminBroadcastStates.waiting_buttons, AdminFilter())
async def admin_broadcast_wait_buttons(msg: Message, state: FSMContext):
    raw = (msg.text or "").strip()
    if not raw:
        await msg.answer("Отправьте текст с названиями кнопок или «пропустить».")
        return

    raw_l = raw.lower()
    if raw_l in {"пропустить", "skip", "без кнопок", "нет"}:
        await state.set_state(AdminBroadcastStates.waiting_text)
        await msg.answer(
            "Ок, кнопок не будет.\n\n"
            "Теперь отправьте <b>текст рассылки</b> (поддерживаются HTML-теги).\n"
            "Например: <code>Привет!</code>",
            reply_markup=admin_broadcast_cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    labels = _parse_button_labels(raw)
    if not labels:
        await msg.answer("Не удалось распознать названия кнопок. Попробуйте ещё раз.")
        return

    data = await state.get_data()
    current: list[str] = list(data.get("button_labels") or [])
    max_buttons = 8
    prev_len = len(current)
    for label in labels[: max_buttons - prev_len]:
        current.append(label)

    await state.update_data(button_labels=current)
    await msg.answer(
        f"Добавлено кнопок: {len(current) - prev_len}. Текущих кнопок: {len(current)}.\n\n"
        "Можно добавить ещё или нажмите «✅ Готово».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Готово", callback_data="adminbroadcast:buttons_done")],
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data="adminbroadcast:cancel")],
            ]
        ),
    )


@router.callback_query(F.data == "adminbroadcast:buttons_done", AdminFilter())
async def admin_broadcast_buttons_done(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(AdminBroadcastStates.waiting_text)
    await cb.message.edit_text(
        "Теперь отправьте <b>текст рассылки</b> (поддерживаются HTML-теги).",
        reply_markup=admin_broadcast_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(AdminBroadcastStates.waiting_text, AdminFilter())
async def admin_broadcast_wait_text(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if not text:
        await msg.answer("Текст не может быть пустым.")
        return

    await state.update_data(message_text=text)
    data = await state.get_data()
    broadcast_id = str(data.get("broadcast_id") or "")
    labels: list[str] = list(data.get("button_labels") or [])
    photo_present = bool(data.get("photo_file_id"))

    buttons_preview = ", ".join(labels) if labels else "нет"
    await msg.answer(
        "Проверьте перед отправкой:\n\n"
        f"Фото: {'да' if photo_present else 'нет'}\n"
        f"Кнопки: {buttons_preview}\n\n"
        "Текст будет отправлен как caption (если есть фото) или как обычное сообщение.\n\n"
        "Отправить всем пользователям?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Отправить всем", callback_data="adminbroadcast:confirm_send")],
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data="adminbroadcast:cancel")],
            ]
        ),
    )


async def _send_broadcast_to_all(bot, admin_chat_id: int, payload: dict) -> None:
    broadcast_id = str(payload.get("broadcast_id") or "")
    photo_file_id = payload.get("photo_file_id")
    labels: list[str] = list(payload.get("button_labels") or [])
    message_text = str(payload.get("message_text") or "")

    kb = _build_broadcast_keyboard(broadcast_id, labels)
    batch_size = 200
    sent_ok = 0
    sent_fail = 0

    total = await count_users()
    await bot.send_message(admin_chat_id, f"⏳ Отправляю рассылку. Пользователей: {total}.")

    offset = 0
    while True:
        user_ids = await list_user_ids(limit=batch_size, offset=offset)
        if not user_ids:
            break

        for uid in user_ids:
            try:
                if photo_file_id:
                    await bot.send_photo(
                        uid,
                        photo_file_id,
                        caption=message_text,
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                else:
                    await bot.send_message(uid, message_text, reply_markup=kb, parse_mode="HTML")
                sent_ok += 1
            except Exception:
                sent_fail += 1

        offset += batch_size
        # небольшая пауза для снижения риска rate-limit.
        await asyncio.sleep(0.25)

    await bot.send_message(admin_chat_id, f"✅ Рассылка завершена.\n\nУспешно: {sent_ok}\nНе удалось: {sent_fail}")


@router.callback_query(F.data == "adminbroadcast:confirm_send", AdminFilter())
async def admin_broadcast_confirm_send(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    if not data.get("message_text"):
        await cb.message.edit_text("Текст рассылки не задан.", reply_markup=admin_broadcast_menu_keyboard())
        await state.clear()
        return

    payload = dict(data)
    await state.clear()

    await cb.message.edit_text("⏳ Запускаю отправку...")
    asyncio.create_task(_send_broadcast_to_all(cb.bot, cb.from_user.id, payload))


@router.callback_query(F.data.startswith("adminbroadcast:btn:"),)
async def admin_broadcast_button_pressed(cb: CallbackQuery):
    # Кнопки в рассылке не являются ссылками, поэтому отвечаем на callback чтобы убрать "залипание".
    await cb.answer()

