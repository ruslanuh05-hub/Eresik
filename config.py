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

# Webhook:
# - если явно задан `USE_WEBHOOK=1` — используем webhook
# - если `USE_WEBHOOK` не задан — используем webhook только когда задан `PUBLIC_BASE_URL`
_use_webhook_env = os.getenv("USE_WEBHOOK", "").strip().lower()
USE_WEBHOOK = _use_webhook_env in {"1", "true", "yes", "y"} if _use_webhook_env else bool(PUBLIC_BASE_URL)
WEBHOOK_PATH = "/webhook"

# Подписка
SUBSCRIPTION_BASE_URL = os.getenv("SUBSCRIPTION_BASE_URL", "https://sub1.jetstoreapp.ru/v2raytun-sub")
UPSTREAM_SUB_URL = os.getenv("UPSTREAM_SUB_URL", SUBSCRIPTION_BASE_URL)

# Фото для личного кабинета (путь к фоновому изображению)
CABINET_BG_IMAGE = Path(__file__).parent / "assets" / "cabinet_bg.png"

# Координаты текста подписки на картинке кабинета:
# TEXT_X — горизонталь: число пикселей или 0.0–1.0 (0.5 = центр)
# TEXT_Y_FROM_BOTTOM — базовая линия Y, пикселей от низа изображения
# LABEL_OFFSET — смещение «Подписка до:» вверх от базы (отрицательное)
# DATE_OFFSET — смещение даты вниз от базы (положительное)
CABINET_TEXT_X = 0.7  # 0.5 = центр
CABINET_TEXT_Y_FROM_BOTTOM = 120
CABINET_LABEL_OFFSET = -50
CABINET_DATE_OFFSET = -1100  # поднять дату/время выше (было 15)

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
