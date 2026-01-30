// database.js - База данных для хранения данных пользователей и товаров
class Database {
    constructor() {
        this.storageKey = 'jetstore_db';
        this.usersKey = 'jetstore_users';
        this.productsKey = 'jetstore_products';
        // ФИКСИРОВАННЫЙ ключ для баланса (независимо от пользователя)
        this.balanceKey = 'jetstore_balance_fixed';
        this.userIdKey = 'jetstore_user_id_fixed';
    }
    
    // Получение фиксированного ID пользователя
    getFixedUserId() {
        try {
            const tg = window.Telegram?.WebApp;
            const initData = tg?.initDataUnsafe;
            const tgId = initData?.user?.id ? String(initData.user.id) : 'test_user_default';

            let storedId = localStorage.getItem(this.userIdKey);

            // Если в localStorage уже был другой пользователь — считаем это новым пользователем
            // и сбрасываем "доступный баланс" на 0.
            if (storedId && tgId && storedId !== tgId) {
                localStorage.setItem(this.userIdKey, tgId);

                // Новый пользователь -> баланс 0
                const zeroBalance = {
                    RUB: 0,
                    TON: 0,
                    USDT: 0,
                    USD: 0,
                    EUR: 0,
                    lastUpdate: new Date().getTime(),
                    _resetReason: 'new_user'
                };
                localStorage.setItem(this.balanceKey, JSON.stringify(zeroBalance));

                return tgId;
            }

            if (!storedId) {
                // Первый запуск для пользователя
                storedId = tgId || 'test_user_default';
                localStorage.setItem(this.userIdKey, storedId);

                // Первый запуск -> баланс 0 (явно фиксируем ключ)
                if (!localStorage.getItem(this.balanceKey)) {
                    const zeroBalance = {
                        RUB: 0,
                        TON: 0,
                        USDT: 0,
                        USD: 0,
                        EUR: 0,
                        lastUpdate: new Date().getTime(),
                        _resetReason: 'first_run'
                    };
                    localStorage.setItem(this.balanceKey, JSON.stringify(zeroBalance));
                }
            }

            return storedId;
        } catch (error) {
            console.error('Ошибка получения фиксированного ID:', error);
            return 'test_user_default';
        }
    }
    
    // Сохранение баланса с фиксированным ключом
    saveBalanceFixed(currency, amount) {
        try {
            const balanceData = JSON.parse(localStorage.getItem(this.balanceKey) || '{}');
            balanceData[currency] = amount;
            balanceData.lastUpdate = new Date().getTime();
            localStorage.setItem(this.balanceKey, JSON.stringify(balanceData));
            
            // Проверяем сохранение
            const check = JSON.parse(localStorage.getItem(this.balanceKey) || '{}');
            if (check[currency] === amount) {
                console.log(`✅✅✅ БАЛАНС ${currency} СОХРАНЕН (фиксированный ключ):`, amount);
                return true;
            }
            return false;
        } catch (error) {
            console.error('Ошибка сохранения баланса (фиксированный):', error);
            return false;
        }
    }
    
    // Получение баланса с фиксированным ключом
    getBalanceFixed(currency = 'RUB') {
        try {
            const balanceData = JSON.parse(localStorage.getItem(this.balanceKey) || '{}');
            return balanceData[currency] || 0;
        } catch (error) {
            console.error('Ошибка получения баланса (фиксированный):', error);
            return 0;
        }
    }

    // Инициализация базы данных
    init() {
        console.log('Инициализация базы данных...');
        
        // Проверяем наличие данных
        if (!localStorage.getItem(this.usersKey)) {
            localStorage.setItem(this.usersKey, JSON.stringify({}));
        }
        
        if (!localStorage.getItem(this.productsKey)) {
            // Загружаем товары из products.json, если есть
            this.loadDefaultProducts();
        }
        
        console.log('База данных инициализирована');
    }

    // Загрузка товаров по умолчанию
    loadDefaultProducts() {
        const defaultProducts = {
            telegram: [
                {
                    id: 'tg_stars_100',
                    name: 'Telegram Stars 100',
                    description: '100 звезд для Telegram',
                    price: 100,
                    category: 'telegram',
                    icon: 'fas fa-star',
                    badge: 'Telegram'
                },
                {
                    id: 'tg_stars_500',
                    name: 'Telegram Stars 500',
                    description: '500 звезд для Telegram',
                    price: 450,
                    category: 'telegram',
                    icon: 'fas fa-star',
                    badge: 'Telegram'
                },
                {
                    id: 'tg_stars_1000',
                    name: 'Telegram Stars 1000',
                    description: '1000 звезд для Telegram',
                    price: 800,
                    category: 'telegram',
                    icon: 'fas fa-star',
                    badge: 'Telegram'
                }
            ],
            steam: [
                {
                    id: 'steam_wallet_500',
                    name: 'Steam Wallet 500₽',
                    description: 'Пополнение кошелька Steam на 500₽',
                    price: 500,
                    category: 'steam',
                    icon: 'fab fa-steam',
                    badge: 'Steam'
                },
                {
                    id: 'steam_wallet_1000',
                    name: 'Steam Wallet 1000₽',
                    description: 'Пополнение кошелька Steam на 1000₽',
                    price: 1000,
                    category: 'steam',
                    icon: 'fab fa-steam',
                    badge: 'Steam'
                }
            ],
            games: [],
            brawlstars: [
                {
                    id: 'brawlstars_test_1',
                    name: 'Brawl Pass',
                    description: 'Тестовый товар для Brawl Stars',
                    price: 299,
                    category: 'brawlstars',
                    icon: 'fas fa-star',
                    badge: 'Brawl Stars'
                }
            ],
            clashroyale: [
                {
                    id: 'clashroyale_test_1',
                    name: 'Royal Pass',
                    description: 'Тестовый товар для Clash Royale',
                    price: 399,
                    category: 'clashroyale',
                    icon: 'fas fa-crown',
                    badge: 'Clash Royale'
                }
            ],
            clashofclans: [
                {
                    id: 'clashofclans_test_1',
                    name: 'Pass',
                    description: 'Тестовый товар для Clash of Clans',
                    price: 349,
                    category: 'clashofclans',
                    icon: 'fas fa-shield-alt',
                    badge: 'Clash of Clans'
                }
            ],
            standoff2: [
                {
                    id: 'standoff2_test_1',
                    name: 'Gold',
                    description: 'Тестовый товар для Standoff 2',
                    price: 199,
                    category: 'standoff2',
                    icon: 'fas fa-coins',
                    badge: 'Standoff 2'
                }
            ],
            pubgmobile: [
                {
                    id: 'pubgmobile_test_1',
                    name: 'UC',
                    description: 'Тестовый товар для PUBG Mobile',
                    price: 249,
                    category: 'pubgmobile',
                    icon: 'fas fa-coins',
                    badge: 'PUBG Mobile'
                }
            ]
        };
        
        localStorage.setItem(this.productsKey, JSON.stringify(defaultProducts));
    }

    // Получение пользователя
    getUser(userId) {
        try {
            const users = JSON.parse(localStorage.getItem(this.usersKey) || '{}');
            return users[userId] || null;
        } catch (error) {
            console.error('Ошибка получения пользователя:', error);
            return null;
        }
    }

    // Сохранение пользователя с несколькими попытками
    saveUser(userData) {
        if (!userData || !userData.id) {
            console.error('❌ Ошибка: userData или userData.id отсутствует!');
            return false;
        }
        
        // Делаем несколько попыток сохранения
        for (let attempt = 1; attempt <= 3; attempt++) {
            try {
                const users = JSON.parse(localStorage.getItem(this.usersKey) || '{}');
                
                // Убеждаемся, что currencies инициализированы
                if (!userData.currencies) {
                    userData.currencies = {
                        RUB: 0,
                        USDT: 0,
                        USD: 0,
                        EUR: 0
                    };
                }
                
                // Сохраняем полную копию данных пользователя
                users[userData.id] = JSON.parse(JSON.stringify(userData)); // Глубокая копия
                
                // Сохраняем в localStorage
                localStorage.setItem(this.usersKey, JSON.stringify(users));
                
                // Сразу проверяем сохранение
                const saved = JSON.parse(localStorage.getItem(this.usersKey) || '{}');
                if (saved[userData.id] && saved[userData.id].currencies) {
                    const savedBalance = saved[userData.id].currencies.RUB;
                    const expectedBalance = userData.currencies.RUB;
                    
                    if (savedBalance === expectedBalance) {
                        console.log(`✅ Пользователь сохранен (попытка ${attempt}):`, userData.id);
                        console.log('✅ Баланс RUB в сохраненных данных:', savedBalance);
                        return true;
                    } else {
                        console.warn(`⚠️ Попытка ${attempt}: Баланс не совпадает. Ожидалось: ${expectedBalance}, Получено: ${savedBalance}`);
                        if (attempt < 3) continue; // Пробуем еще раз
                    }
                } else {
                    console.warn(`⚠️ Попытка ${attempt}: Данные не найдены после сохранения`);
                    if (attempt < 3) continue; // Пробуем еще раз
                }
            } catch (error) {
                console.error(`❌ Ошибка сохранения пользователя (попытка ${attempt}):`, error);
                if (attempt < 3) {
                    // Небольшая задержка перед следующей попыткой
                    setTimeout(() => {}, 10);
                    continue;
                }
                console.error('Stack:', error.stack);
                return false;
            }
        }
        
        console.error('❌ Не удалось сохранить после 3 попыток!');
        return false;
    }
    
    // Быстрое сохранение баланса (только баланс)
    saveBalance(userId, currency, amount) {
        try {
            const users = JSON.parse(localStorage.getItem(this.usersKey) || '{}');
            if (!users[userId]) {
                console.error('❌ Пользователь не найден для сохранения баланса');
                return false;
            }
            
            if (!users[userId].currencies) {
                users[userId].currencies = {};
            }
            
            users[userId].currencies[currency] = amount;
            localStorage.setItem(this.usersKey, JSON.stringify(users));
            
            // Проверяем сохранение
            const saved = JSON.parse(localStorage.getItem(this.usersKey) || '{}');
            if (saved[userId] && saved[userId].currencies && saved[userId].currencies[currency] === amount) {
                console.log(`✅ Баланс ${currency} сохранен:`, amount);
                return true;
            }
            return false;
        } catch (error) {
            console.error('❌ Ошибка сохранения баланса:', error);
            return false;
        }
    }

    // Получение всех товаров
    getProducts() {
        try {
            return JSON.parse(localStorage.getItem(this.productsKey) || '{}');
        } catch (error) {
            console.error('Ошибка получения товаров:', error);
            return {};
        }
    }

    // Получение товаров по категории
    getProductsByCategory(category) {
        try {
            const products = this.getProducts();
            return products[category] || [];
        } catch (error) {
            console.error('Ошибка получения товаров по категории:', error);
            return [];
        }
    }

    // Сохранение товаров
    saveProducts(products) {
        try {
            localStorage.setItem(this.productsKey, JSON.stringify(products));
            console.log('Товары сохранены');
            return true;
        } catch (error) {
            console.error('Ошибка сохранения товаров:', error);
            return false;
        }
    }

    // Добавление товара
    addProduct(product) {
        try {
            const products = this.getProducts();
            const category = product.category || 'all';
            
            if (!products[category]) {
                products[category] = [];
            }
            
            products[category].push(product);
            this.saveProducts(products);
            return true;
        } catch (error) {
            console.error('Ошибка добавления товара:', error);
            return false;
        }
    }

    // Удаление товара
    removeProduct(productId, category) {
        try {
            const products = this.getProducts();
            if (products[category]) {
                products[category] = products[category].filter(p => p.id !== productId);
                this.saveProducts(products);
                return true;
            }
            return false;
        } catch (error) {
            console.error('Ошибка удаления товара:', error);
            return false;
        }
    }

    // Получение всех пользователей (для админки)
    getAllUsers() {
        try {
            return JSON.parse(localStorage.getItem(this.usersKey) || '{}');
        } catch (error) {
            console.error('Ошибка получения всех пользователей:', error);
            return {};
        }
    }
    
    // Получение курсов валют
    getCurrencyRates() {
        try {
            const defaultRates = {
                RUB: 1,
                USDT: 80,
                USD: 90,
                EUR: 100
            };
            const saved = JSON.parse(localStorage.getItem('jetstore_currency_rates') || '{}');
            return { ...defaultRates, ...saved };
        } catch (error) {
            console.error('Ошибка получения курсов валют:', error);
            return { RUB: 1, USDT: 80, USD: 90, EUR: 100 };
        }
    }
    
    // Обновление курсов валют
    updateCurrencyRates(rates) {
        try {
            localStorage.setItem('jetstore_currency_rates', JSON.stringify(rates));
            // Отдельно сохраняем курс USDT для profile.js
            if (rates.USDT) {
                localStorage.setItem('jetstore_usdt_rate', rates.USDT.toString());
            }
            console.log('✅ Курсы валют сохранены:', rates);
            return true;
        } catch (error) {
            console.error('Ошибка сохранения курсов валют:', error);
            return false;
        }
    }
}

// Создаем глобальный экземпляр базы данных
if (typeof window !== 'undefined') {
    window.Database = new Database();
    console.log('✅ Database создан и доступен глобально через window.Database');
    console.log('✅ Database.getUser:', typeof window.Database.getUser);
    console.log('✅ Database.saveBalanceFixed:', typeof window.Database.saveBalanceFixed);
} else {
    console.error('❌ window не определен!');
}
