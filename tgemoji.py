"""ID кастомных эмодзи Telegram (Fragment / Premium) и разметка <tg-emoji>."""


class E:
    """Соответствие из скриншота пользователя."""

    HEART = "4996980495100150380"  # приветствие (внутри тега — ❤️)
    ARROW_DOWN = "5406745015365943482"
    USER_HEADER = "5904630315946611415"  # заголовок «Личный кабинет», кнопка «Профиль»
    USER_NICK = "5920344347152224466"  # строка «Ник»
    MONEY = "5897958754267174109"  # баланс, админ
    CALENDAR = "5967782394080530708"  # подписка до / дата
    CLOCK = "593617080716745162"  # осталось


def tg(emoji_id: str, fallback: str) -> str:
    """HTML-фрагмент для parse_mode=HTML."""
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
