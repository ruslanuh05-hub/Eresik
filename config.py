"""Конфигурация бота."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# База данных
# Render: DATABASE_URL создаётся автоматически при добавлении PostgreSQL
# Локально: не задавайте — будет использоваться SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent))
DB_PATH = DATA_DIR / "jvpn_bot.db"

# FreeKassa (https://docs.freekassa.net/)
FREKASSA_SHOP_ID = os.getenv("FREKASSA_SHOP_ID", "")
FREKASSA_SECRET_1 = os.getenv("FREKASSA_SECRET_1", "")
FREKASSA_SECRET_2 = os.getenv("FREKASSA_SECRET_2", "")

# URL для callback FreeKassa (должен быть публичный, например https://yourdomain.com)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
FREKASSA_CALLBACK_PATH = "/pay/freekassa/callback"

# Подписка
SUBSCRIPTION_BASE_URL = os.getenv("SUBSCRIPTION_BASE_URL", "https://sub1.jetstoreapp.ru/v2raytun-sub")
UPSTREAM_SUB_URL = os.getenv("UPSTREAM_SUB_URL", SUBSCRIPTION_BASE_URL)

# Фото для личного кабинета (путь к фоновому изображению)
CABINET_BG_IMAGE = Path(__file__).parent / "assets" / "cabinet_bg.png"

# Фото для главного меню (команда /start)
WELCOME_IMAGE = Path(__file__).parent / "assets" / "welcome.png"

# Тарифы: id -> (дни, название). Цена = дни * price_per_day
DEFAULT_PRICE_PER_DAY = 70 / 30  # 70 ₽/месяц изначально
PLAN_DAYS = {
    "d7": (7, "7 дней"),
    "d30": (30, "30 дней"),
    "d60": (60, "60 дней"),
    "d90": (90, "90 дней"),
}
