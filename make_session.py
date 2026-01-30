import os
import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main():
    api_id_raw = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()

    # Если переменные окружения не заданы — спросим в консоли
    if not api_id_raw:
        api_id_raw = input("Введите TELEGRAM_API_ID: ").strip()
    if not api_hash:
        api_hash = input("Введите TELEGRAM_API_HASH: ").strip()

    if not api_id_raw or not api_hash:
        print("❌ TELEGRAM_API_ID и TELEGRAM_API_HASH обязательны")
        return

    api_id = int(api_id_raw)

    print("🔐 Создаём STRING_SESSION (Telethon userbot)")
    print("Дальше будет запрос номера/кода/пароля (если включена 2FA).")
    print("")

    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        # Telethon сам запросит телефон/код/2FA в консоли
        session_str = client.session.save()

    print("")
    print("✅ ГОТОВО. TELEGRAM_STRING_SESSION:")
    print(session_str)
    print("")
    print("Сохрани это в переменную окружения TELEGRAM_STRING_SESSION и запускай bot.py.")


if __name__ == "__main__":
    asyncio.run(main())

