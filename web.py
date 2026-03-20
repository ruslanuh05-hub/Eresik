"""Веб-сервер для FreeKassa callback и выдачи подписок."""
import logging
import time
from aiohttp import web
import httpx

from config import FREKASSA_CALLBACK_PATH, UPSTREAM_SUB_URL

logger = logging.getLogger("jvpn-web")
from database import (
    get_payment_by_order_id,
    add_payment,
    add_balance,
    update_payment_status_by_order_id,
    get_subscription_by_token,
    get_subscription_record_by_token,
)
from freekassa import verify_callback


async def freekassa_callback(request: web.Request) -> web.Response:
    """
    Обработчик callback от FreeKassa.
    FreeKassa отправляет: MERCHANT_ID, AMOUNT, MERCHANT_ORDER_ID, SIGN
    Должен вернуть YES при успешной обработке.
    """
    if request.method != "POST":
        return web.Response(status=405, text="Method not allowed")

    try:
        data = await request.post()
    except Exception:
        return web.Response(status=400, text="Bad request")

    merchant_id = str(data.get("MERCHANT_ID", "")).strip()
    amount = str(data.get("AMOUNT", "")).strip().replace(",", ".")
    order_id = str(data.get("MERCHANT_ORDER_ID", "")).strip()
    sign = str(data.get("SIGN", "")).strip()

    if not all([merchant_id, amount, sign]) or not order_id:
        logger.warning("FreeKassa callback: missing params")
        return web.Response(status=400, text="Missing params")

    if not verify_callback(merchant_id, amount, order_id, sign):
        logger.warning("FreeKassa callback: invalid sign for order_id=%s", order_id[:50])
        return web.Response(status=403, text="Invalid sign")

    payment = await get_payment_by_order_id(order_id)
    if payment and payment.get("status") == "completed":
        return web.Response(text="YES")

    if not payment:
        # Платёж не найден - возможно order_id от FreeKassa в другом формате
        # Пробуем создать по формату jvpn_telegramid_timestamp
        parts = order_id.split("_")
        if len(parts) >= 2 and parts[0] == "jvpn":
            try:
                tg_id = int(parts[1])
                amt = float(amount)
                await add_payment(tg_id, amt, order_id, order_id, "completed")
                new_balance = await add_balance(tg_id, amt)
                await _notify_payment_success(request, tg_id, amt, new_balance)
                return web.Response(text="YES")
            except (ValueError, IndexError) as e:
                logger.warning("FreeKassa callback: fallback parse failed for order_id=%s: %s", order_id[:50], e)
        logger.warning("FreeKassa callback: order not found, order_id=%s", order_id[:50])
        return web.Response(status=404, text="Order not found")

    tg_id = payment["telegram_id"]
    await update_payment_status_by_order_id(order_id, "completed")
    new_balance = await add_balance(tg_id, float(amount))
    await _notify_payment_success(request, tg_id, float(amount), new_balance)
    return web.Response(text="YES")


async def _notify_payment_success(request: web.Request, telegram_id: int, amount: float, new_balance: float):
    """Уведомить пользователя об успешном пополнении."""
    bot = request.app.get("bot")
    if bot:
        try:
            await bot.send_message(
                telegram_id,
                f"✅ Баланс пополнен на *{amount:.2f} ₽*\n\nТекущий баланс: *{new_balance:.2f} ₽*",
            )
        except Exception:
            pass


async def subscription_handler(request: web.Request) -> web.Response:
    """Выдать подписку по токену (проксирует upstream с проверкой срока)."""
    token = request.match_info.get("token", "").removesuffix(".txt")
    try:
        if not token or len(token) < 10:
            return web.Response(status=404, text="Not found")

        # Важно для Happ: даже если срок уже прошёл (или Happ делает запрос сразу после покупки),
        # вернём конфиг с тем expire, который хранится в БД по токену.
        sub = await get_subscription_record_by_token(token)
        if not sub:
            return web.Response(status=403, text="Subscription expired or not found")

        if not UPSTREAM_SUB_URL:
            return web.Response(status=502, text="Upstream not configured")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(UPSTREAM_SUB_URL)
                resp.raise_for_status()
                body = resp.text
        except Exception:
            return web.Response(status=502, text="Upstream not available")

        expires = sub.get("subscription_expires_at")
        if expires is None:
            return web.Response(status=403, text="Subscription expired or invalid expires")
        try:
            expire_unix = int(expires)
        except Exception as e:
            logger.exception("Bad subscription_expires_at type (token=%s): %s", token[:12], e)
            return web.Response(status=500, text="Bad subscription expires")

        # Заменяем expire в subscription-userinfo на персональный срок
        lines = body.split("\n")
        new_lines = []
        userinfo_replaced = False
        for line in lines:
            if line.strip().startswith("# subscription-userinfo:"):
                # Подставляем наш expire
                new_lines.append(
                    f"# subscription-userinfo: upload=0; download=0; total=1073741824000; expire={expire_unix}"
                )
                userinfo_replaced = True
                continue
            new_lines.append(line)
        if not userinfo_replaced:
            new_lines.insert(0, f"# subscription-userinfo: upload=0; download=0; total=1073741824000; expire={expire_unix}")
            new_lines.insert(0, "")

        result = "\n".join(new_lines)
        return web.Response(
            text=result,
            content_type="text/plain",
            headers={"Cache-Control": "no-store"},
        )
    except Exception as e:
        logger.exception("subscription_handler failed (token=%s): %s", (token or "")[:12], e)
        # Happ "падает" на 500 — в качестве fallback отдадим upstream подписку как есть.
        # Так импорт хотя бы состоится, а ошибку мы увидим в логах.
        if UPSTREAM_SUB_URL:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(UPSTREAM_SUB_URL)
                    resp.raise_for_status()
                    body = resp.text
                return web.Response(
                    text=body,
                    content_type="text/plain",
                    headers={"Cache-Control": "no-store"},
                )
            except Exception as upstream_err:
                logger.exception("subscription_handler fallback upstream failed: %s", upstream_err)

        # Самое последнее: отдаём 200 с пустой "служебной" заглушкой,
        # чтобы клиент не показывал 500.
        return web.Response(
            status=200,
            text="# subscription-userinfo: upload=0; download=0; total=0; expire=0\n",
            content_type="text/plain",
            headers={"Cache-Control": "no-store"},
        )


def create_app(bot=None) -> web.Application:
    """Создать aiohttp приложение. bot нужен для уведомлений (опционально)."""
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", lambda r: web.json_response({"ok": True, "service": "jvpn-bot"}))
    app.router.add_get("/health", lambda r: web.json_response({"ok": True}))
    app.router.add_post(FREKASSA_CALLBACK_PATH, freekassa_callback)
    app.router.add_get("/sub/{token}.txt", subscription_handler)
    app.router.add_get("/debug/sub/{token}.txt", debug_subscription_handler)
    # Debug без суффикса .txt (на случай, если клиент открывает другой формат)
    app.router.add_get("/debug/sub/{token}", debug_subscription_handler)
    return app


async def debug_subscription_handler(request: web.Request) -> web.Response:
    """Debug: показать что хранится по токену подписки."""
    token = request.match_info.get("token", "").removesuffix(".txt")
    try:
        record = await get_subscription_record_by_token(token)
        if not record:
            return web.json_response({"token": token, "found": False})

        from time import time as now_time

        expires = record.get("subscription_expires_at")
        return web.json_response(
            {
                "token": token,
                "found": True,
                "telegram_id": record.get("telegram_id"),
                "subscription_expires_at": expires,
                "now": int(now_time()),
                "active": bool(expires is not None and int(expires) > int(now_time())),
            }
        )
    except Exception as e:
        logger.exception("debug_subscription_handler failed (token=%s): %s", token[:12], e)
        return web.json_response({"error": "internal_error"})
