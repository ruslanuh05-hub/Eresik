"""Интеграция FreeKassa для пополнения баланса."""
import hashlib
import urllib.parse
from typing import Optional

import hmac
import json
import time

import httpx

from config import (
    FREKASSA_API_KEY,
    FREKASSA_SHOP_ID,
    FREKASSA_SECRET_1,
    FREKASSA_SECRET_2,
    FREKASSA_SERVER_IP,
    PUBLIC_BASE_URL,
    FREKASSA_CALLBACK_PATH,
)


def _sign_payment(amount: float, order_id: str, secret: str) -> str:
    """
    Подпись для формы оплаты (SCI).
    По документации: MD5(ID_магазина:Сумма:Secret1:Валюта:Номер_заказа)
    """
    s = f"{FREKASSA_SHOP_ID}:{amount:.2f}:{secret}:RUB:{order_id}"
    return hashlib.md5(s.encode()).hexdigest()


def _sign_callback(merchant_id: str, amount: str, order_id: str, secret: str) -> str:
    """Подпись для проверки callback: MD5(merchant_id:amount:secret:order_id)."""
    s = f"{merchant_id}:{amount}:{secret}:{order_id}"
    return hashlib.md5(s.encode()).hexdigest()


def create_payment_url(amount: float, order_id: str, telegram_id: int) -> Optional[str]:
    """
    Создать ссылку на оплату FreeKassa.
    order_id должен быть уникальным (например order_123_1234567890).
    """
    if not all([FREKASSA_SHOP_ID, FREKASSA_SECRET_1]):
        return None

    sign = _sign_payment(amount, order_id, FREKASSA_SECRET_1)
    params = {
        "m": FREKASSA_SHOP_ID,
        "oa": f"{amount:.2f}",
        "o": order_id,
        "s": sign,
        # У FreeKassa для формы pay.fk.money в примерах используется pay=PAY.
        # Без этого параметра некоторые магазины/настройки не открывают форму оплаты.
        "pay": "PAY",
        "currency": "RUB",
        "lang": "ru",
        "us_telegram_id": str(telegram_id),
    }
    return f"https://pay.fk.money/?{urllib.parse.urlencode(params)}"


def _api_signature(data: dict) -> str:
    """
    Подпись запросов API FreeKassa:
    - сортируем по ключам
    - конкатенируем значения через |
    - HMAC-SHA256 с FREKASSA_API_KEY
    """
    items = {k: v for k, v in data.items() if k != "signature"}
    # Важно: порядок ключей по алфавиту, значения как строки.
    base = "|".join(str(items[k]) for k in sorted(items.keys()))
    return hmac.new(FREKASSA_API_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()

_LAST_NONCE: int = 0


def _next_nonce() -> int:
    """Nonce должен всегда быть больше предыдущего значения."""
    global _LAST_NONCE
    n = int(time.time() * 1000)
    if n <= _LAST_NONCE:
        n = _LAST_NONCE + 1
    _LAST_NONCE = n
    return n


async def create_payment_url_api(amount: float, order_id: str, telegram_id: int) -> Optional[str]:
    """
    Создать заказ через FreeKassa API и получить ссылку на оплату.
    Док: POST https://api.fk.life/v1/orders/create
    """
    if not FREKASSA_API_KEY or not FREKASSA_SHOP_ID:
        return None

    nonce = _next_nonce()
    if not FREKASSA_SERVER_IP:
        # по инструкции нельзя 127.0.0.1; нужен публичный IP сервера (или реальный IP, если есть).
        return None

    payload = {
        "shopId": int(FREKASSA_SHOP_ID),
        "nonce": nonce,
        "paymentId": order_id,
        # i будет передаваться параметром (см. ниже)
        # Email/IP обязательны в доке. В Telegram они не доступны — ставим безопасный плейсхолдер.
        "email": f"{telegram_id}@telegram.org",
        "ip": str(FREKASSA_SERVER_IP),
        # Важно: для подписи используем строку с 2 знаками, как в большинстве SDK/примеров.
        "amount": f"{amount:.2f}",
        "currency": "RUB",
        "notification_url": get_callback_url(),
    }
    # payment system id (i) добавим ниже в create_payment_url_api_with_method
    payload["signature"] = _api_signature(payload)

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                "https://api.fk.life/v1/orders/create",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    if not isinstance(data, dict) or str(data.get("type")) != "success":
        return None

    # В документации есть поле location, иногда пустое — тогда собираем ссылку из orderId/orderHash.
    loc = str(data.get("location") or "").strip()
    if loc:
        return loc
    order_id_fk = data.get("orderId")
    order_hash = data.get("orderHash")
    if order_id_fk and order_hash:
        return f"https://pay.freekassa.net/form/{order_id_fk}/{order_hash}"
    return None


async def create_payment_url_api_with_method(
    amount: float,
    order_id: str,
    telegram_id: int,
    payment_system_i: int,
) -> Optional[str]:
    """
    Создать заказ через FreeKassa API и вернуть ссылку.

    payment_system_i:
      44 - СБП (QR)
      36 - Карты РФ
      43 - SberPay
    """
    if not FREKASSA_API_KEY or not FREKASSA_SHOP_ID:
        return None

    if not FREKASSA_SERVER_IP:
        return None

    nonce = _next_nonce()
    payload = {
        "shopId": int(FREKASSA_SHOP_ID),
        "nonce": nonce,
        "paymentId": order_id,
        "i": int(payment_system_i),
        "email": f"{telegram_id}@telegram.org",
        "ip": str(FREKASSA_SERVER_IP),
        "amount": f"{amount:.2f}",
        "currency": "RUB",
        "notification_url": get_callback_url(),
    }
    payload["signature"] = _api_signature(payload)

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                "https://api.fk.life/v1/orders/create",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    if not isinstance(data, dict) or str(data.get("type")) != "success":
        return None

    loc = str(data.get("location") or "").strip()
    if loc:
        return loc
    order_id_fk = data.get("orderId")
    order_hash = data.get("orderHash")
    if order_id_fk and order_hash:
        return f"https://pay.freekassa.net/form/{order_id_fk}/{order_hash}"
    return None


def verify_callback(merchant_id: str, amount: str, order_id: str, sign: str) -> bool:
    """Проверить подпись callback от FreeKassa (SECRET_2)."""
    if not FREKASSA_SECRET_2:
        return False
    expected = _sign_callback(merchant_id, amount, order_id, FREKASSA_SECRET_2)
    return sign.lower() == expected.lower()


def get_callback_url() -> str:
    """URL для callback FreeKassa (должен быть указан в ЛК FreeKassa)."""
    return f"{PUBLIC_BASE_URL}{FREKASSA_CALLBACK_PATH}"
