"""Фон для экрана профиля: без текста на изображении (даты в подписи сообщения)."""
import io

from PIL import Image

from config import CABINET_BG_IMAGE


def generate_subscription_image(expires_at: int | None = None, nickname: str = "") -> bytes:
    """
    Возвращает PNG фона кабинета.
    Аргументы expires_at и nickname оставлены для совместимости вызовов — на картинку не влияют.
    """
    if CABINET_BG_IMAGE.exists():
        img = Image.open(CABINET_BG_IMAGE).convert("RGB")
    else:
        img = Image.new("RGB", (400, 200), color=(30, 35, 45))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
