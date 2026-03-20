"""Главный файл: запуск бота и веб-сервера (aiogram + asyncio)."""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import BOT_TOKEN, ADMIN_IDS, PUBLIC_BASE_URL, USE_WEBHOOK, WEBHOOK_PATH
from database import init_db
from web import create_app
from handlers.start import router as start_router
from handlers.cabinet import router as cabinet_router
from handlers.topup import router as topup_router
from handlers.buy import router as buy_router
from handlers.admin import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("jvpn-bot")


async def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set. Create .env from .env.example")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(cabinet_router)
    dp.include_router(topup_router)
    dp.include_router(buy_router)
    dp.include_router(admin_router)

    @dp.error()
    async def handle_error(event: ErrorEvent) -> bool:
        """Перехват TelegramBadRequest: 'message is not modified' (повторные нажатия)."""
        if isinstance(event.exception, TelegramBadRequest) and "message is not modified" in str(event.exception):
            if event.update.callback_query:
                await event.update.callback_query.answer()
            return True
        return False

    # Web-server routes (FreeKassa callback + /sub/{token}.txt)
    app = create_app(bot)
    runner = web.AppRunner(app)

    # Aiohttp webhook integration for aiogram
    if USE_WEBHOOK and PUBLIC_BASE_URL:
        webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

    await init_db()

    # When using webhook: tell Telegram our webhook URL.
    if USE_WEBHOOK and PUBLIC_BASE_URL:
        await bot.set_webhook(f"{PUBLIC_BASE_URL}{WEBHOOK_PATH}")
        logger.info("Webhook set to %s%s", PUBLIC_BASE_URL, WEBHOOK_PATH)

    # Notify admins on startup
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🟢 JetVPN бот запущен.")
        except Exception:
            pass

    # Start aiohttp server
    web_port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8089")))
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", web_port)
    await site.start()
    logger.info("Web server started on port %s (webhook=%s)", web_port, USE_WEBHOOK)

    try:
        if USE_WEBHOOK and PUBLIC_BASE_URL:
            await asyncio.Event().wait()
        else:
            # Явно включаем типы обновлений, которые используются хендлерами (включая callback_query).
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if USE_WEBHOOK and PUBLIC_BASE_URL:
            await bot.delete_webhook()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
