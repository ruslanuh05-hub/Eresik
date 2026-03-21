"""Веб-сервер для FreeKassa callback и выдачи подписок."""
import logging
import time
import urllib.parse
from aiohttp import web
import httpx

from config import (
    FREKASSA_CALLBACK_PATH,
    UPSTREAM_SUB_URL,
    PUBLIC_BRAND_NAME,
    PUBLIC_TG_URL,
    PUBLIC_SITE_URL,
)

logger = logging.getLogger("jvpn-web")
from database import (
    get_payment_by_order_id,
    add_payment,
    add_balance,
    update_payment_status_by_order_id,
    get_subscription_by_token,
    get_subscription_record_by_token,
    get_user_by_telegram_id,
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

        # Если ссылку открыли в обычном браузере, не показываем сырой vless-список.
        user_agent = (request.headers.get("User-Agent") or "").lower()
        is_browser = ("mozilla" in user_agent) and ("happ" not in user_agent) and ("hiddify" not in user_agent) and ("v2raytun" not in user_agent)
        if is_browser:
            sub_url = str(request.url)
            happ_link = f"happ://import/{sub_url}"
            hiddify_link = f"hiddify://import/{sub_url}#JetVPN"
            v2raytun_link = f"v2raytun://import/{sub_url}"
            tg_id = sub.get("telegram_id")
            user = await get_user_by_telegram_id(int(tg_id)) if tg_id is not None else None
            user_name = "-"
            if user:
                user_name = user.get("nickname") or user.get("username") or f"user_{tg_id}"
            expire_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(expire_unix))
            remain_sec = max(0, expire_unix - int(time.time()))
            remain_days = remain_sec // 86400
            remain_hours = (remain_sec % 86400) // 3600
            remain_str = f"{remain_days} дн. {remain_hours} ч." if remain_days > 0 else f"{remain_hours} ч."
            html = f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{PUBLIC_BRAND_NAME} Подписка</title>
  <style>
    body {{ font-family: Arial, sans-serif; background:#0b1220; color:#fff; margin:0; padding:24px; }}
    .box {{ max-width:700px; margin:0 auto; background:#111827; padding:20px; border-radius:14px; border:1px solid #1f2937; }}
    .top {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; }}
    .brand {{ font-size:26px; font-weight:700; }}
    .links a {{ color:#93c5fd; text-decoration:none; margin-left:10px; }}
    .meta {{ background:#0f172a; border:1px solid #1f2937; border-radius:10px; padding:12px; margin:14px 0; }}
    .meta p {{ margin:6px 0; color:#d1d5db; }}
    a.btn {{ display:block; text-decoration:none; color:#fff; background:#2563eb; padding:12px 14px; border-radius:10px; margin:10px 0; text-align:center; }}
    code {{ word-break:break-all; display:block; background:#1f2937; padding:10px; border-radius:8px; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="top">
      <div class="brand">{PUBLIC_BRAND_NAME}</div>
      <div class="links">
        <a href="{PUBLIC_TG_URL}" target="_blank" rel="noopener">Telegram</a>
        <a href="{PUBLIC_SITE_URL}" target="_blank" rel="noopener">Сайт</a>
      </div>
    </div>
    <div class="meta">
      <p><b>Пользователь:</b> {user_name}</p>
      <p><b>Действует до:</b> {expire_str}</p>
      <p><b>Осталось:</b> {remain_str}</p>
    </div>
    <p>Откройте подписку в приложении:</p>
    <a class="btn" href="{happ_link}">Открыть в Happ</a>
    <a class="btn" href="{hiddify_link}">Открыть в Hiddify</a>
    <a class="btn" href="{v2raytun_link}">Открыть в v2RayTun</a>
    <p>Если кнопки не сработали, скопируйте URL и вставьте в приложение вручную:</p>
    <code>{sub_url}</code>
  </div>
</body>
</html>
            """.strip()
            return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})

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
