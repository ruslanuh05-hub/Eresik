"""База данных: PostgreSQL (Render) или SQLite (локально). Таблицы с суффиксом Jvpn."""
import aiosqlite
import asyncpg
import secrets
import time
from pathlib import Path
from typing import Optional

from config import DB_PATH, DEFAULT_PRICE_PER_DAY, PLAN_DAYS, DATABASE_URL

# Имена таблиц с суффиксом Jvpn (для Render)
USERS_TABLE = "usersJvpn"
PAYMENTS_TABLE = "paymentsJvpn"
PURCHASES_TABLE = "purchasesJvpn"
SETTINGS_TABLE = "settingsJvpn"
SERVERS_TABLE = "serversJvpn"
ADMIN_KEYS_TABLE = "adminkeysJvpn"
BROADCASTS_TABLE = "broadcastsJvpn"

USE_POSTGRES = bool(DATABASE_URL)


def _pg_url() -> str:
    """asyncpg требует postgresql://, Render может отдавать postgres://"""
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql://" + url[10:]
    return url


def _now() -> int:
    return int(time.time())


def _create_token() -> str:
    return secrets.token_urlsafe(24)


async def init_db() -> None:
    """Создаёт таблицы если их нет."""
    if USE_POSTGRES:
        await _init_pg()
    else:
        await _init_sqlite()


async def _init_pg() -> None:
    conn = await asyncpg.connect(_pg_url())
    try:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{USERS_TABLE}" (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                nickname TEXT,
                balance DOUBLE PRECISION NOT NULL DEFAULT 0,
                subscription_expires_at BIGINT,
                subscription_token TEXT,
                referral_bonus_claimed INTEGER NOT NULL DEFAULT 0,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{PAYMENTS_TABLE}" (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                order_id TEXT,
                freekassa_order_id TEXT,
                status TEXT NOT NULL,
                created_at BIGINT NOT NULL
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{PURCHASES_TABLE}" (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                plan_id TEXT NOT NULL,
                days INTEGER NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                created_at BIGINT NOT NULL
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SETTINGS_TABLE}" (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at BIGINT NOT NULL
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{SERVERS_TABLE}" (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                country_code TEXT,
                limits INTEGER NOT NULL DEFAULT 0,
                online_count INTEGER NOT NULL DEFAULT 0,
                load_value INTEGER NOT NULL DEFAULT 0,
                is_online BOOLEAN NOT NULL DEFAULT false,
                created_at BIGINT NOT NULL
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{ADMIN_KEYS_TABLE}" (
                id SERIAL PRIMARY KEY,
                key_value TEXT NOT NULL UNIQUE,
                owner_telegram_id BIGINT,
                expires_at BIGINT,
                traffic_limit_bytes BIGINT,
                traffic_used_bytes BIGINT NOT NULL DEFAULT 0,
                created_at BIGINT NOT NULL
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{BROADCASTS_TABLE}" (
                id SERIAL PRIMARY KEY,
                created_by BIGINT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                message_text TEXT NOT NULL,
                buttons_json TEXT,
                scheduled_at BIGINT,
                sent_at BIGINT,
                created_at BIGINT NOT NULL
            )
        """)
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_payments_order_Jvpn 
            ON "{PAYMENTS_TABLE}" (freekassa_order_id)
        """)
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_payments_merchant_order_Jvpn 
            ON "{PAYMENTS_TABLE}" (order_id)
        """)
        row = await conn.fetchrow(f'SELECT 1 FROM "{SETTINGS_TABLE}" WHERE key = $1', "price_per_day")
        if not row:
            await conn.execute(
                f'INSERT INTO "{SETTINGS_TABLE}" (key, value, updated_at) VALUES ($1, $2, $3) ON CONFLICT (key) DO NOTHING',
                "price_per_day", str(DEFAULT_PRICE_PER_DAY), _now(),
            )
        await conn.execute(
            f'ALTER TABLE "{USERS_TABLE}" ADD COLUMN IF NOT EXISTS referral_bonus_claimed INTEGER NOT NULL DEFAULT 0',
        )
    finally:
        await conn.close()


async def _init_sqlite() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                nickname TEXT,
                balance REAL NOT NULL DEFAULT 0,
                subscription_expires_at INTEGER,
                subscription_token TEXT,
                referral_bonus_claimed INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {PAYMENTS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                order_id TEXT,
                freekassa_order_id TEXT,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {PURCHASES_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                plan_id TEXT NOT NULL,
                days INTEGER NOT NULL,
                amount REAL NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {SETTINGS_TABLE} (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {SERVERS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                country_code TEXT,
                limits INTEGER NOT NULL DEFAULT 0,
                online_count INTEGER NOT NULL DEFAULT 0,
                load_value INTEGER NOT NULL DEFAULT 0,
                is_online INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
        """)
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {ADMIN_KEYS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_value TEXT NOT NULL UNIQUE,
                owner_telegram_id INTEGER,
                expires_at INTEGER,
                traffic_limit_bytes INTEGER,
                traffic_used_bytes INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
        """)
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {BROADCASTS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_by INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                message_text TEXT NOT NULL,
                buttons_json TEXT,
                scheduled_at INTEGER,
                sent_at INTEGER,
                created_at INTEGER NOT NULL
            )
        """)
        await db.execute(f"CREATE INDEX IF NOT EXISTS idx_payments_order_Jvpn ON {PAYMENTS_TABLE}(freekassa_order_id)")
        await db.execute(f"CREATE INDEX IF NOT EXISTS idx_payments_merchant_order_Jvpn ON {PAYMENTS_TABLE}(order_id)")
        cur = await db.execute(f'SELECT 1 FROM {SETTINGS_TABLE} WHERE key = ?', ("price_per_day",))
        if not await cur.fetchone():
            await db.execute(
                f"INSERT OR IGNORE INTO {SETTINGS_TABLE} (key, value, updated_at) VALUES (?, ?, ?)",
                ("price_per_day", str(DEFAULT_PRICE_PER_DAY), _now()),
            )
        cur_cols = await db.execute(f"PRAGMA table_info({USERS_TABLE})")
        cols = [r[1] for r in await cur_cols.fetchall()]
        if "referral_bonus_claimed" not in cols:
            await db.execute(
                f"ALTER TABLE {USERS_TABLE} ADD COLUMN referral_bonus_claimed INTEGER NOT NULL DEFAULT 0"
            )
        await db.commit()


async def get_or_create_user(telegram_id: int, username: str | None = None) -> dict:
    """Получить или создать пользователя."""
    if USE_POSTGRES:
        return await _get_or_create_user_pg(telegram_id, username)
    return await _get_or_create_user_sqlite(telegram_id, username)


async def _get_or_create_user_pg(telegram_id: int, username: str | None) -> dict:
    conn = await asyncpg.connect(_pg_url())
    try:
        row = await conn.fetchrow(f'SELECT * FROM "{USERS_TABLE}" WHERE telegram_id = $1', telegram_id)
        if row:
            return dict(row)

        now = _now()
        nickname = username or f"user_{telegram_id}"
        token = _create_token()
        await conn.execute(
            f'''INSERT INTO "{USERS_TABLE}" (telegram_id, username, nickname, balance, subscription_expires_at,
               subscription_token, referral_bonus_claimed, created_at, updated_at)
               VALUES ($1, $2, $3, 0, NULL, $4, 0, $5, $5)''',
            telegram_id, username or "", nickname, token, now,
        )
    finally:
        await conn.close()
    return await _get_or_create_user_pg(telegram_id, username)


async def _get_or_create_user_sqlite(telegram_id: int, username: str | None) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(f"SELECT * FROM {USERS_TABLE} WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)

        now = _now()
        nickname = username or f"user_{telegram_id}"
        token = _create_token()
        await db.execute(
            f"""INSERT INTO {USERS_TABLE} (telegram_id, username, nickname, balance, subscription_expires_at,
               subscription_token, referral_bonus_claimed, created_at, updated_at)
               VALUES (?, ?, ?, 0, NULL, ?, 0, ?, ?)""",
            (telegram_id, username or "", nickname, token, now, now),
        )
        await db.commit()
    return await _get_or_create_user_sqlite(telegram_id, username)


async def update_user(telegram_id: int, **kwargs) -> None:
    """Обновить поля пользователя."""
    allowed = {"username", "nickname", "balance", "subscription_expires_at", "subscription_token", "referral_bonus_claimed"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = _now()
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            set_parts = ", ".join(f'"{k}" = ${i+1}' for i, k in enumerate(updates))
            values = list(updates.values()) + [telegram_id]
            await conn.execute(
                f'UPDATE "{USERS_TABLE}" SET {set_parts} WHERE telegram_id = ${len(values)}',
                *values,
            )
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [telegram_id]
            await db.execute(f"UPDATE {USERS_TABLE} SET {set_clause} WHERE telegram_id = ?", values)
            await db.commit()


async def add_balance(telegram_id: int, amount: float) -> float:
    """Пополнить баланс. Возвращает новый баланс."""
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            await conn.execute(
                f'UPDATE "{USERS_TABLE}" SET balance = balance + $1, updated_at = $2 WHERE telegram_id = $3',
                amount, _now(), telegram_id,
            )
            row = await conn.fetchrow(f'SELECT balance FROM "{USERS_TABLE}" WHERE telegram_id = $1', telegram_id)
            return float(row["balance"]) if row else 0
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                f"UPDATE {USERS_TABLE} SET balance = balance + ?, updated_at = ? WHERE telegram_id = ?",
                (amount, _now(), telegram_id),
            )
            await db.commit()
            cur = await db.execute(f"SELECT balance FROM {USERS_TABLE} WHERE telegram_id = ?", (telegram_id,))
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_subscription_by_token(token: str) -> Optional[dict]:
    """Проверить подписку по токену (активна и не истекла)."""
    now = _now()
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(
                f'SELECT telegram_id, subscription_expires_at FROM "{USERS_TABLE}" '
                f'WHERE subscription_token = $1 AND subscription_expires_at > $2',
                token, now,
            )
            return dict(row) if row else None
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                f"SELECT telegram_id, subscription_expires_at FROM {USERS_TABLE} "
                f"WHERE subscription_token = ? AND subscription_expires_at > ?",
                (token, now),
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_subscription_record_by_token(token: str) -> Optional[dict]:
    """
    Debug/helper: вернуть запись подписки по token независимо от expire.
    Возвращает telegram_id и subscription_expires_at, чтобы понять что хранится в БД.
    """
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(
                f'SELECT telegram_id, subscription_expires_at, subscription_token FROM "{USERS_TABLE}" '
                f'WHERE subscription_token = $1',
                token,
            )
            return dict(row) if row else None
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                f"SELECT telegram_id, subscription_expires_at, subscription_token FROM {USERS_TABLE} WHERE subscription_token = ?",
                (token,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    """Получить пользователя по telegram_id без создания новой записи."""
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(
                f'SELECT * FROM "{USERS_TABLE}" WHERE telegram_id = $1',
                telegram_id,
            )
            return dict(row) if row else None
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                f"SELECT * FROM {USERS_TABLE} WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_by_username(username: str) -> Optional[dict]:
    """Поиск пользователя по username (без @)."""
    username = (username or "").strip()
    if username.startswith("@"):
        username = username[1:]
    if not username:
        return None

    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(f'SELECT * FROM "{USERS_TABLE}" WHERE username = $1', username)
            return dict(row) if row else None
        finally:
            await conn.close()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(f"SELECT * FROM {USERS_TABLE} WHERE username = ?", (username,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def list_users(limit: int = 50) -> list[dict]:
    """Список пользователей (для админа)."""
    limit = max(1, min(int(limit), 200))
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            rows = await conn.fetch(
                f'SELECT * FROM "{USERS_TABLE}" ORDER BY created_at DESC LIMIT $1',
                limit,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(f"SELECT * FROM {USERS_TABLE} ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def count_users() -> int:
    """Общее количество пользователей в БД."""
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            total = await conn.fetchval(f'SELECT COUNT(1) FROM "{USERS_TABLE}"')
            return int(total or 0)
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(f"SELECT COUNT(1) FROM {USERS_TABLE}")
        row = await cur.fetchone()
        return int(row[0] or 0) if row else 0


async def list_user_ids(limit: int = 500, offset: int = 0) -> list[int]:
    """
    Порция telegram_id для рассылки.

    Используется чтобы отправлять "всех" без загрузки всей таблицы в память.
    """
    limit = max(1, min(int(limit), 2000))
    offset = max(0, int(offset))
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            rows = await conn.fetch(
                f'SELECT telegram_id FROM "{USERS_TABLE}" ORDER BY created_at DESC LIMIT $1 OFFSET $2',
                limit,
                offset,
            )
            return [int(r["telegram_id"]) for r in rows]
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            f"SELECT telegram_id FROM {USERS_TABLE} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cur.fetchall()
        return [int(r[0]) for r in rows]


async def reset_subscription_token(telegram_id: int) -> str:
    """Сбросить токен подписки для пользователя."""
    token = _create_token()
    await update_user(telegram_id, subscription_token=token)
    return token


async def block_subscription(telegram_id: int) -> None:
    """Блокировать подписку: сбросить expire и обновить токен."""
    token = await reset_subscription_token(telegram_id)
    await update_user(telegram_id, subscription_expires_at=0, subscription_token=token)


async def create_or_extend_subscription(telegram_id: int, days: int, plan_id: str, cost: float) -> tuple[str, int]:
    """Создать или продлить подписку. Возвращает (token, expires_at)."""
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(
                f'SELECT balance, subscription_expires_at, subscription_token FROM "{USERS_TABLE}" WHERE telegram_id = $1',
                telegram_id,
            )
            if not row:
                raise ValueError("User not found")
            if float(row["balance"]) < cost:
                raise ValueError("Недостаточно средств на балансе")

            now = _now()
            current_expires = row["subscription_expires_at"] or 0
            new_expires = (current_expires + days * 86400) if current_expires > now else (now + days * 86400)
            token = row["subscription_token"] or _create_token()

            await conn.execute(
                f'''UPDATE "{USERS_TABLE}" SET balance = balance - $1, subscription_expires_at = $2,
                    subscription_token = $3, updated_at = $4 WHERE telegram_id = $5''',
                cost, new_expires, token, now, telegram_id,
            )
            await conn.execute(
                f'INSERT INTO "{PURCHASES_TABLE}" (telegram_id, plan_id, days, amount, created_at) VALUES ($1, $2, $3, $4, $5)',
                telegram_id, plan_id, days, cost, now,
            )
        finally:
            await conn.close()
        return token, new_expires
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                f"SELECT balance, subscription_expires_at, subscription_token FROM {USERS_TABLE} WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cur.fetchone()
            if not row:
                raise ValueError("User not found")
            if row["balance"] < cost:
                raise ValueError("Недостаточно средств на балансе")
            now = _now()
            current_expires = row["subscription_expires_at"] or 0
            new_expires = (current_expires + days * 86400) if current_expires > now else (now + days * 86400)
            token = row["subscription_token"] or _create_token()
            await db.execute(
                f"""UPDATE {USERS_TABLE} SET balance = balance - ?, subscription_expires_at = ?,
                    subscription_token = ?, updated_at = ? WHERE telegram_id = ?""",
                (cost, new_expires, token, now, telegram_id),
            )
            await db.execute(
                f"INSERT INTO {PURCHASES_TABLE} (telegram_id, plan_id, days, amount, created_at) VALUES (?, ?, ?, ?, ?)",
                (telegram_id, plan_id, days, cost, now),
            )
            await db.commit()
        return token, new_expires


async def add_gift_subscription_days(telegram_id: int, days: int, plan_id: str) -> tuple[str, int]:
    """Продлить подписку на N дней без списания баланса (бонусы, рефералка)."""
    if days <= 0:
        raise ValueError("days must be positive")
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(
                f'SELECT subscription_expires_at, subscription_token FROM "{USERS_TABLE}" WHERE telegram_id = $1',
                telegram_id,
            )
            if not row:
                raise ValueError("User not found")
            now = _now()
            current_expires = row["subscription_expires_at"] or 0
            add_sec = days * 86400
            new_expires = (current_expires + add_sec) if current_expires > now else (now + add_sec)
            token = row["subscription_token"] or _create_token()
            await conn.execute(
                f'''UPDATE "{USERS_TABLE}" SET subscription_expires_at = $1,
                    subscription_token = $2, updated_at = $3 WHERE telegram_id = $4''',
                new_expires, token, now, telegram_id,
            )
            await conn.execute(
                f'INSERT INTO "{PURCHASES_TABLE}" (telegram_id, plan_id, days, amount, created_at) VALUES ($1, $2, $3, $4, $5)',
                telegram_id, plan_id, days, 0.0, now,
            )
        finally:
            await conn.close()
        return token, new_expires
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            f"SELECT subscription_expires_at, subscription_token FROM {USERS_TABLE} WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise ValueError("User not found")
        now = _now()
        current_expires = row["subscription_expires_at"] or 0
        add_sec = days * 86400
        new_expires = (current_expires + add_sec) if current_expires > now else (now + add_sec)
        token = row["subscription_token"] or _create_token()
        await db.execute(
            f"""UPDATE {USERS_TABLE} SET subscription_expires_at = ?,
                subscription_token = ?, updated_at = ? WHERE telegram_id = ?""",
            (new_expires, token, now, telegram_id),
        )
        await db.execute(
            f"INSERT INTO {PURCHASES_TABLE} (telegram_id, plan_id, days, amount, created_at) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, plan_id, days, 0.0, now),
        )
        await db.commit()
    return token, new_expires


async def _gift_days_conn_pg(
    conn: asyncpg.Connection,
    telegram_id: int,
    days: int,
    plan_id: str,
    now: int,
) -> None:
    row = await conn.fetchrow(
        f'SELECT subscription_expires_at, subscription_token FROM "{USERS_TABLE}" WHERE telegram_id = $1',
        telegram_id,
    )
    if not row:
        raise ValueError("User not found")
    current_expires = row["subscription_expires_at"] or 0
    add_sec = days * 86400
    new_expires = (current_expires + add_sec) if current_expires > now else (now + add_sec)
    token = row["subscription_token"] or _create_token()
    await conn.execute(
        f'''UPDATE "{USERS_TABLE}" SET subscription_expires_at = $1,
            subscription_token = $2, updated_at = $3 WHERE telegram_id = $4''',
        new_expires,
        token,
        now,
        telegram_id,
    )
    await conn.execute(
        f'INSERT INTO "{PURCHASES_TABLE}" (telegram_id, plan_id, days, amount, created_at) VALUES ($1, $2, $3, $4, $5)',
        telegram_id,
        plan_id,
        days,
        0.0,
        now,
    )


async def apply_referral_bonus(referee_id: int, referrer_id: int) -> bool:
    """
    Один раз: приглашённому +3 дня, пригласившему +3 дня.
    Возвращает False, если бонус уже был или реферер совпадает с пользователем.
    """
    if referee_id == referrer_id:
        return False
    now = _now()
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            async with conn.transaction():
                claimed = await conn.fetchrow(
                    f'''UPDATE "{USERS_TABLE}" SET referral_bonus_claimed = 1, updated_at = $1
                        WHERE telegram_id = $2 AND referral_bonus_claimed = 0
                        RETURNING telegram_id''',
                    now,
                    referee_id,
                )
                if not claimed:
                    return False
                ref_row = await conn.fetchrow(
                    f'SELECT telegram_id FROM "{USERS_TABLE}" WHERE telegram_id = $1',
                    referrer_id,
                )
                if not ref_row:
                    await conn.execute(
                        f'''INSERT INTO "{USERS_TABLE}" (telegram_id, username, nickname, balance,
                            subscription_expires_at, subscription_token, referral_bonus_claimed,
                            created_at, updated_at)
                            VALUES ($1, $2, $3, 0, NULL, $4, 0, $5, $5)''',
                        referrer_id,
                        "",
                        f"user_{referrer_id}",
                        _create_token(),
                        now,
                    )
                await _gift_days_conn_pg(conn, referee_id, 3, "ref_referee_bonus", now)
                await _gift_days_conn_pg(conn, referrer_id, 3, "ref_referrer_bonus", now)
            return True
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        try:
            cur_u = await db.execute(
                f"UPDATE {USERS_TABLE} SET referral_bonus_claimed = 1, updated_at = ? "
                f"WHERE telegram_id = ? AND referral_bonus_claimed = 0 "
                f"RETURNING telegram_id",
                (now, referee_id),
            )
            row_claim = await cur_u.fetchone()
            if not row_claim:
                await db.rollback()
                return False
            cur2 = await db.execute(f"SELECT 1 FROM {USERS_TABLE} WHERE telegram_id = ?", (referrer_id,))
            if not await cur2.fetchone():
                token_r = _create_token()
                await db.execute(
                    f"""INSERT INTO {USERS_TABLE} (telegram_id, username, nickname, balance,
                        subscription_expires_at, subscription_token, referral_bonus_claimed, created_at, updated_at)
                        VALUES (?, ?, ?, 0, NULL, ?, 0, ?, ?)""",
                    (referrer_id, "", f"user_{referrer_id}", token_r, now, now),
                )
            for uid, days, pid in (
                (referee_id, 3, "ref_referee_bonus"),
                (referrer_id, 3, "ref_referrer_bonus"),
            ):
                cur = await db.execute(
                    f"SELECT subscription_expires_at, subscription_token FROM {USERS_TABLE} WHERE telegram_id = ?",
                    (uid,),
                )
                row = await cur.fetchone()
                if not row:
                    await db.rollback()
                    return False
                current_expires = row["subscription_expires_at"] or 0
                add_sec = days * 86400
                new_expires = (current_expires + add_sec) if current_expires > now else (now + add_sec)
                token_u = row["subscription_token"] or _create_token()
                await db.execute(
                    f"""UPDATE {USERS_TABLE} SET subscription_expires_at = ?,
                        subscription_token = ?, updated_at = ? WHERE telegram_id = ?""",
                    (new_expires, token_u, now, uid),
                )
                await db.execute(
                    f"INSERT INTO {PURCHASES_TABLE} (telegram_id, plan_id, days, amount, created_at) VALUES (?, ?, ?, ?, ?)",
                    (uid, pid, days, 0.0, now),
                )
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return True


async def add_payment(telegram_id: int, amount: float, order_id: str, freekassa_order_id: str, status: str) -> None:
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            await conn.execute(
                f'INSERT INTO "{PAYMENTS_TABLE}" (telegram_id, amount, order_id, freekassa_order_id, status, created_at) '
                f'VALUES ($1, $2, $3, $4, $5, $6)',
                telegram_id, amount, order_id, freekassa_order_id, status, _now(),
            )
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                f"INSERT INTO {PAYMENTS_TABLE} (telegram_id, amount, order_id, freekassa_order_id, status, created_at) "
                f"VALUES (?, ?, ?, ?, ?, ?)",
                (telegram_id, amount, order_id, freekassa_order_id, status, _now()),
            )
            await db.commit()


async def get_payment_by_freekassa_id(freekassa_order_id: str) -> Optional[dict]:
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(
                f'SELECT * FROM "{PAYMENTS_TABLE}" WHERE freekassa_order_id = $1',
                freekassa_order_id,
            )
            return dict(row) if row else None
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(f"SELECT * FROM {PAYMENTS_TABLE} WHERE freekassa_order_id = ?", (freekassa_order_id,))
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_payment_by_order_id(order_id: str) -> Optional[dict]:
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(f'SELECT * FROM "{PAYMENTS_TABLE}" WHERE order_id = $1', order_id)
            return dict(row) if row else None
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(f"SELECT * FROM {PAYMENTS_TABLE} WHERE order_id = ?", (order_id,))
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_payment_status_by_order_id(order_id: str, status: str, freekassa_order_id: str = "") -> None:
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            if freekassa_order_id:
                await conn.execute(
                    f'UPDATE "{PAYMENTS_TABLE}" SET status = $1, freekassa_order_id = $2 WHERE order_id = $3',
                    status, freekassa_order_id, order_id,
                )
            else:
                await conn.execute(f'UPDATE "{PAYMENTS_TABLE}" SET status = $1 WHERE order_id = $2', status, order_id)
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            if freekassa_order_id:
                await db.execute(
                    f"UPDATE {PAYMENTS_TABLE} SET status = ?, freekassa_order_id = ? WHERE order_id = ?",
                    (status, freekassa_order_id, order_id),
                )
            else:
                await db.execute(f"UPDATE {PAYMENTS_TABLE} SET status = ? WHERE order_id = ?", (status, order_id))
            await db.commit()


async def get_payment_by_id(payment_id: int) -> Optional[dict]:
    """Получить платеж по id (для админки)."""
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(f'SELECT * FROM "{PAYMENTS_TABLE}" WHERE id = $1', payment_id)
            return dict(row) if row else None
        finally:
            await conn.close()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(f"SELECT * FROM {PAYMENTS_TABLE} WHERE id = ?", (payment_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def list_payments(limit: int = 20, status: str | None = None) -> list[dict]:
    """Список платежей (для админки)."""
    limit = max(1, min(int(limit), 100))
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            if status:
                rows = await conn.fetch(
                    f'SELECT * FROM "{PAYMENTS_TABLE}" WHERE status = $1 ORDER BY created_at DESC LIMIT $2',
                    status,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    f'SELECT * FROM "{PAYMENTS_TABLE}" ORDER BY created_at DESC LIMIT $1',
                    limit,
                )
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cur = await db.execute(
                f"SELECT * FROM {PAYMENTS_TABLE} WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cur = await db.execute(f"SELECT * FROM {PAYMENTS_TABLE} ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def update_payment_status_by_id(payment_id: int, status: str) -> None:
    """Обновить статус платежа по id (админка)."""
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            await conn.execute(f'UPDATE "{PAYMENTS_TABLE}" SET status = $1 WHERE id = $2', status, payment_id)
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(f"UPDATE {PAYMENTS_TABLE} SET status = ? WHERE id = ?", (status, payment_id))
            await db.commit()


async def list_servers(limit: int = 50) -> list[dict]:
    """Список серверов (для админки)."""
    limit = max(1, min(int(limit), 200))
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            rows = await conn.fetch(
                f'SELECT * FROM "{SERVERS_TABLE}" ORDER BY created_at DESC LIMIT $1',
                limit,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            f"SELECT * FROM {SERVERS_TABLE} ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def list_admin_keys(limit: int = 50) -> list[dict]:
    """Список ключей админ-доступа (абстракция в БД)."""
    limit = max(1, min(int(limit), 200))
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            rows = await conn.fetch(
                f'SELECT * FROM "{ADMIN_KEYS_TABLE}" ORDER BY created_at DESC LIMIT $1',
                limit,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            f"SELECT * FROM {ADMIN_KEYS_TABLE} ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_admin_stats() -> dict:
    """Сводка для админки."""
    now = _now()
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            active_users = await conn.fetchval(
                f'SELECT COUNT(1) FROM "{USERS_TABLE}" WHERE subscription_expires_at IS NOT NULL AND subscription_expires_at > $1',
                now,
            )
            total_users = await conn.fetchval(f'SELECT COUNT(1) FROM "{USERS_TABLE}"')
            revenue_completed = await conn.fetchval(
                f'SELECT COALESCE(SUM(amount), 0) FROM "{PAYMENTS_TABLE}" WHERE status = $1',
                "completed",
            )
            revenue_pending = await conn.fetchval(
                f'SELECT COALESCE(SUM(amount), 0) FROM "{PAYMENTS_TABLE}" WHERE status = $1',
                "pending",
            )
            servers_online = await conn.fetchval(
                f'SELECT COALESCE(SUM(CASE WHEN is_online THEN 1 ELSE 0 END), 0) FROM "{SERVERS_TABLE}"',
            )
            return {
                "total_users": int(total_users or 0),
                "active_users": int(active_users or 0),
                "revenue_completed": float(revenue_completed or 0),
                "revenue_pending": float(revenue_pending or 0),
                "servers_online": int(servers_online or 0),
            }
        finally:
            await conn.close()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            f"SELECT COUNT(1) FROM {USERS_TABLE} WHERE subscription_expires_at IS NOT NULL AND subscription_expires_at > ?",
            (now,),
        )
        active_users = (await cur.fetchone())[0]
        cur = await db.execute(f"SELECT COUNT(1) FROM {USERS_TABLE}")
        total_users = (await cur.fetchone())[0]
        cur = await db.execute(f"SELECT COALESCE(SUM(amount), 0) FROM {PAYMENTS_TABLE} WHERE status = ?", ("completed",))
        revenue_completed = (await cur.fetchone())[0]
        cur = await db.execute(f"SELECT COALESCE(SUM(amount), 0) FROM {PAYMENTS_TABLE} WHERE status = ?", ("pending",))
        revenue_pending = (await cur.fetchone())[0]
        cur = await db.execute(f"SELECT COUNT(1) FROM {SERVERS_TABLE} WHERE is_online = 1")
        servers_online = (await cur.fetchone())[0]
        return {
            "total_users": int(total_users or 0),
            "active_users": int(active_users or 0),
            "revenue_completed": float(revenue_completed or 0),
            "revenue_pending": float(revenue_pending or 0),
            "servers_online": int(servers_online or 0),
        }


async def update_payment_status(freekassa_order_id: str, status: str) -> None:
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            await conn.execute(
                f'UPDATE "{PAYMENTS_TABLE}" SET status = $1 WHERE freekassa_order_id = $2',
                status, freekassa_order_id,
            )
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                f"UPDATE {PAYMENTS_TABLE} SET status = ? WHERE freekassa_order_id = ?",
                (status, freekassa_order_id),
            )
            await db.commit()


async def get_price_per_day() -> float:
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            row = await conn.fetchrow(f'SELECT value FROM "{SETTINGS_TABLE}" WHERE key = $1', "price_per_day")
            if row:
                try:
                    return float(row["value"])
                except (ValueError, TypeError):
                    pass
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(f"SELECT value FROM {SETTINGS_TABLE} WHERE key = ?", ("price_per_day",))
            row = await cur.fetchone()
            if row:
                try:
                    return float(row[0])
                except (ValueError, TypeError):
                    pass
    return DEFAULT_PRICE_PER_DAY


async def set_price_per_day(price: float) -> None:
    if price <= 0 or price > 1000:
        raise ValueError("Цена должна быть от 0.01 до 1000 ₽")
    now = _now()
    if USE_POSTGRES:
        conn = await asyncpg.connect(_pg_url())
        try:
            await conn.execute(
                f'INSERT INTO "{SETTINGS_TABLE}" (key, value, updated_at) VALUES ($1, $2, $3) '
                f'ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = $3',
                "price_per_day", str(price), now,
            )
        finally:
            await conn.close()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                f"INSERT OR REPLACE INTO {SETTINGS_TABLE} (key, value, updated_at) VALUES (?, ?, ?)",
                ("price_per_day", str(price), now),
            )
            await db.commit()


async def get_plans() -> list[dict]:
    """Список тарифов. Цена = дни × price_per_day (округлено)."""
    price_per_day = await get_price_per_day()
    return [
        {
            "id": pid,
            "days": days,
            "price": max(1, round(days * price_per_day)),
            "title": title,
        }
        for pid, (days, title) in PLAN_DAYS.items()
    ]
