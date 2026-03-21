# JetVPN Telegram Bot

Телеграм-бот для продажи VPN-подписок с пополнением через FreeKassa и личным кабинетом.

## Возможности

- **Личный кабинет** — баланс, срок подписки, ник, ссылка на подписку
- **Пополнение баланса** — через FreeKassa (суммы 99, 199, 499, 999 ₽ или своя)
- **Покупка подписки** — тарифы 7, 30, 60, 90 дней за баланс
- **Персональная подписка** — каждому пользователю своя ссылка с учётом срока действия

## Установка

```bash
cd jvpn-bot
python -m venv venv
venv\Scripts\activate   # Windows
# или: source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## Настройка

1. Скопируйте `.env.example` в `.env`
2. Заполните переменные:

```env
BOT_TOKEN=токен_от_BotFather
ADMIN_IDS=123456789
FREKASSA_SHOP_ID=ваш_id
FREKASSA_SECRET_1=секретное_слово_1
FREKASSA_SECRET_2=секретное_слово_2
PUBLIC_BASE_URL=https://ваш-домен.com
```

3. **FreeKassa**: в личном кабинете FreeKassa укажите:
   - URL оповещения: `https://ваш-домен.com/pay/freekassa/callback`
   - Метод: POST

4. **Публичный URL**: сервер должен быть доступен по HTTPS (для callback FreeKassa). Можно использовать nginx + reverse proxy.

## Запуск

```bash
python main.py
```

По умолчанию веб-сервер слушает порт 8089. Для production используйте nginx перед приложением.

## Тарифы и админка

Цена считается как **дни × цена_за_день**. Изначально: 70 ₽/месяц ≈ 2.33 ₽/день.

- **Команда /admin** (только для ID из ADMIN_IDS) — изменение цены за 1 день
- Тарифы: 7, 30, 60, 90 дней — цены пересчитываются автоматически

## Подписка

- **UPSTREAM_SUB_URL** — ссылка на ваш HAP/v2ray (например `https://sub1.jetstoreapp.ru/v2raytun-sub`)
- Бот проксирует конфиги и подставляет персональный срок действия (`expire`) для каждого пользователя
- Ссылка подписки: `{PUBLIC_BASE_URL}/sub/{token}.txt`

## Деплой на Render

1. New + → Web Service, подключите репозиторий
2. **Root Directory:** `jvpn-bot`
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `python main.py`
5. Добавьте PostgreSQL и переменную `DATABASE_URL`
6. Заполните: BOT_TOKEN, ADMIN_IDS, FreeKassa, PUBLIC_BASE_URL

Таблицы в БД с суффиксом Jvpn: `usersJvpn`, `paymentsJvpn`, `purchasesJvpn`, `settingsJvpn`

## Структура

```
jvpn-bot/
├── main.py       # Точка входа
├── config.py     # Конфигурация
├── database.py   # PostgreSQL (Render) / SQLite (локально)
├── freekassa.py  # FreeKassa SCI
├── web.py        # Callback + /sub/{token}.txt
├── handlers/     # Хендлеры бота
└── requirements.txt
```

## Команды бота

- `/start` — главное меню
- `/my` или `/cabinet` — личный кабинет
