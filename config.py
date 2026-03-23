"""Конфигурация бота."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Профиль с <tg-emoji>: только если ID из tgemoji доступны этому боту (иначе DOCUMENT_INVALID).
CABINET_PREMIUM_EMOJI = os.getenv("CABINET_PREMIUM_EMOJI", "").lower() in ("1", "true", "yes")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
PUBLIC_BRAND_NAME = os.getenv("PUBLIC_BRAND_NAME", "JetVpn")
PUBLIC_TG_URL = os.getenv("PUBLIC_TG_URL", "https://t.me/2helper")
PUBLIC_SITE_URL = os.getenv("PUBLIC_SITE_URL", "https://sub1.jetstoreapp.ru/v2raytun-sub")
# Отображаемое имя бота в юридических текстах (как в Telegram)
PUBLIC_BOT_DISPLAY = os.getenv("PUBLIC_BOT_DISPLAY", "@jetvpnpro_bot")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@JetStoreHelper")
# Юридические документы (Telegraph)
PRIVACY_POLICY_URL = os.getenv(
    "PRIVACY_POLICY_URL",
    "https://telegra.ph/POLITIKA-KONFIDENCIALNOSTI-03-21-29",
)
TERMS_URL = os.getenv(
    "TERMS_URL",
    "https://telegra.ph/POLZOVATELSKOE-SOGLASHENIE-03-21-31",
)
CONTACT_INFO_URL = os.getenv(
    "CONTACT_INFO_URL",
    "https://telegra.ph/KONTAKTNAYA-INFORMACIYA-03-21",
)
ABOUT_URL = os.getenv("ABOUT_URL", "https://example.com/about")

# Видео/страницы инструкций по платформам
GUIDE_ANDROID_URL = os.getenv("GUIDE_ANDROID_URL", "https://example.com/guide/android")
GUIDE_IOS_URL = os.getenv("GUIDE_IOS_URL", "https://example.com/guide/ios")
GUIDE_ANDROID_TV_URL = os.getenv("GUIDE_ANDROID_TV_URL", "https://example.com/guide/android-tv")
GUIDE_PC_URL = os.getenv("GUIDE_PC_URL", "https://example.com/guide/pc")
# Прямые ссылки на видео (mp4/file_id). Если пусто — бот отправит GUIDE_*_URL.
GUIDE_ANDROID_VIDEO = os.getenv("GUIDE_ANDROID_VIDEO", "")
GUIDE_IOS_VIDEO = os.getenv("GUIDE_IOS_VIDEO", "")
GUIDE_ANDROID_TV_VIDEO = os.getenv("GUIDE_ANDROID_TV_VIDEO", "")
GUIDE_PC_VIDEO = os.getenv("GUIDE_PC_VIDEO", "")

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
# База для HTTPS-страниц импорта (/open/...) в Telegram-кнопках
IMPORT_BRIDGE_BASE = os.getenv("IMPORT_BRIDGE_BASE", "").strip().rstrip("/") or PUBLIC_BASE_URL
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

# Фото для личного кабинета (фон без текста на изображении)
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
