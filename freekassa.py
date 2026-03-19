"""Интеграция FreeKassa для пополнения баланса."""
import hashlib
import urllib.parse
from typing import Optional

from config import FREKASSA_SHOP_ID, FREKASSA_SECRET_1, FREKASSA_SECRET_2, PUBLIC_BASE_URL, FREKASSA_CALLBACK_PATH


def _sign_payment(amount: float, order_id: str, secret: str) -> str:
    """Подпись для формы оплаты: MD5(merchant_id:amount:secret:order_id)."""
    s = f"{FREKASSA_SHOP_ID}:{amount:.2f}:{secret}:{order_id}"
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
        "currency": "RUB",
        "lang": "ru",
        "us_telegram_id": str(telegram_id),
    }
    return f"https://pay.fk.money/?{urllib.parse.urlencode(params)}"


def verify_callback(merchant_id: str, amount: str, order_id: str, sign: str) -> bool:
    """Проверить подпись callback от FreeKassa (SECRET_2)."""
    if not FREKASSA_SECRET_2:
        return False
    expected = _sign_callback(merchant_id, amount, order_id, FREKASSA_SECRET_2)
    return sign.lower() == expected.lower()


def get_callback_url() -> str:
    """URL для callback FreeKassa (должен быть указан в ЛК FreeKassa)."""
    return f"{PUBLIC_BASE_URL}{FREKASSA_CALLBACK_PATH}"
