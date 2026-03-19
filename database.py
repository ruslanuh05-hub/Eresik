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
            CREATE INDEX IF NOT EXISTS idx_payments_order_Jvpn 
            ON "{PAYMENTS_TABLE}" (freekassa_order_id)
        """)
        row = await conn.fetchrow(f'SELECT 1 FROM "{SETTINGS_TABLE}" WHERE key = $1', "price_per_day")
        if not row:
            await conn.execute(
                f'INSERT INTO "{SETTINGS_TABLE}" (key, value, updated_at) VALUES ($1, $2, $3) ON CONFLICT (key) DO NOTHING',
                "price_per_day", str(DEFAULT_PRICE_PER_DAY), _now(),
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
        await db.execute(f"CREATE INDEX IF NOT EXISTS idx_payments_order_Jvpn ON {PAYMENTS_TABLE}(freekassa_order_id)")
        cur = await db.execute(f'SELECT 1 FROM {SETTINGS_TABLE} WHERE key = ?', ("price_per_day",))
        if not await cur.fetchone():
            await db.execute(
                f"INSERT OR IGNORE INTO {SETTINGS_TABLE} (key, value, updated_at) VALUES (?, ?, ?)",
                ("price_per_day", str(DEFAULT_PRICE_PER_DAY), _now()),
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
               subscription_token, created_at, updated_at)
               VALUES ($1, $2, $3, 0, NULL, $4, $5, $5)''',
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
               subscription_token, created_at, updated_at)
               VALUES (?, ?, ?, 0, NULL, ?, ?, ?)""",
            (telegram_id, username or "", nickname, token, now, now),
        )
        await db.commit()
    return await _get_or_create_user_sqlite(telegram_id, username)


async def update_user(telegram_id: int, **kwargs) -> None:
    """Обновить поля пользователя."""
    allowed = {"username", "nickname", "balance", "subscription_expires_at", "subscription_token"}
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
