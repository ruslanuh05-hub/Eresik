"""ID кастомных эмодзи Telegram (Fragment / Premium) и разметка <tg-emoji>."""


class E:
    """ID из скринов пользователя (parse_mode=HTML, тег <tg-emoji>)."""

    HEART = "4996980495100150380"
    ARROW_DOWN = "5406745015365943482"
    USER_HEADER = "5904630315946611415"
    USER_NICK = "5920344347152224466"
    MONEY = "5897958754267174109"
    CALENDAR = "5967782394080530708"
    CLOCK = "593617080716745162"

    # Рефералы / инструкция / платформы (скрин 2)
    REFERRAL = "5931347928810526429"  # 👥
    INSTRUCTION_BOOKMARK = "5222444124698853913"  # 🏷️
    IOS_APPLE = "581892083764867167"  # 🍏 (скрин)
    ANDROID_ROBOT = "5819078828017849357"  # 🤖
    TV = "5967411695453213733"  # 📺
    PC_LAPTOP = "5967816500415827773"  # 💻


def tg(emoji_id: str, fallback: str) -> str:
    """HTML-фрагмент для parse_mode=HTML (в подписи к фото не работает — только в тексте)."""
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
