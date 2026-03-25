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
    MOLNY = "5345905193005371012"  # ⚡️ (новый premium id)
    FORME = "5775869215047160245"  # «форма» / о нас
    PROF = "5784911985221048409"  # профиль
    HELP = "5911274703367968100"  # поддержка
    BACKARROW = "5983279327574233274"
    PARTY = "5193209274452425995"  # 🎉
    GIFT = "5193085063998224234"  # 🎁
    TAG = "5895542564580234154"  # 🏷
    SUPPORT_BOT = "5983582264502523326"  # 🤖
    DOC = "5789864365981175420"  # 📄

    # Рефералы / инструкция / платформы
    REFERRAL = "5931347928810526429"  # 👥
    INSTRUCTION_BOOKMARK = "5906762234633130643"  # 🔗 (новый premium id)
    IOS_APPLE = "5775870512127283512"  # 🍏
    ANDROID_ROBOT = "5019726744978981602"  # 🤖
    TV = "5967411695453213733"  # 📺
    PC_LAPTOP = "5431376038628171216"  # 💻
    PROFILE_DOT = "5415726114104418638"  # 🔵
    PROFILE_MONEY = "5996797032763760544"  # 🪙
    PROFILE_CLOCK = "5983287256083862087"  # ⏰️
    PROFILE_FILM = "5789926071776317562"  # 🎞


def tg(emoji_id: str, fallback: str) -> str:
    """HTML-фрагмент для parse_mode=HTML (в подписи к фото не работает — только в тексте)."""
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
