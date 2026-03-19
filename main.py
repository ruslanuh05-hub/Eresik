"""Главный файл: запуск бота и веб-сервера."""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from config import BOT_TOKEN, ADMIN_IDS
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


async def on_startup(bot: Bot, *args):
    """При старте: инициализация БД и уведомление админам."""
    await init_db()
    logger.info("Database initialized")
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🟢 JetVPN бот запущен.")
        except Exception:
            pass


async def main():
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

    app = create_app(bot)
    runner = web.AppRunner(app)

    # Render задаёт PORT; локально можно WEB_PORT или 8089
    web_port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8089")))

    await init_db()
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", web_port)
    await site.start()
    logger.info("Web server started on port %s", web_port)

    dp.startup.register(on_startup)
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
