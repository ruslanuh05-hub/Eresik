"""ID кастомных эмодзи Telegram (Fragment / Premium) и разметка <tg-emoji>."""

# Премиум на inline/reply-кнопках: icon_custom_emoji_id=E.…
# В сообщениях HTML: tg(E.…, "…") + parse_mode=HTML.


class E:
    """ID из скринов пользователя (parse_mode=HTML, тег <tg-emoji>)."""

    HEART = "5449468596952507859"
    ARROW_DOWN = "5436016445848831807"
    USER_HEADER = "5904630315946611415"
    USER_NICK = "5920344347152224466"
    MONEY = "6016948847517896678"
    CALENDAR = "5967782394080530708"
    CLOCK = "593617080716745162"

    # Нижнее меню (reply): ID для справки / для текста сообщений через tg()
    MOLNY = "5848394616922969249"  # молния → префикс кнопки «Подписка»
    FORME = "5775869215047160245"  # «форма» / о нас
    PROF = "5784911985221048409"  # профиль
    HELP = "5911274703367968100"  # поддержка
    BACKARROW = "5983279327574233274"

    # Рефералы / инструкция / платформы
    REFERRAL = "5931347928810526429"  # 👥
    INSTRUCTION_BOOKMARK = "5222444124698853913"  # 🏷️
    IOS_APPLE = "581892083764867167"  # 🍏
    ANDROID_ROBOT = "5819078828017849357"  # 🤖
    TV = "5967411695453213733"  # 📺
    PC_LAPTOP = "5967816500415827773"  # 💻


def tg(emoji_id: str, fallback: str) -> str:
    """HTML-фрагмент для parse_mode=HTML (в подписи к фото не работает — только в тексте)."""
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
