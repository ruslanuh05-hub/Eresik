// admin.js - Скрипт для админ-панели 

// Текущее состояние
let currentAdminSection = 'stats';
let currentCategory = 'telegram';
let currentEditingProduct = null;
let currentEditingUser = null;

// Инициализация админки
function initAdmin() {
    console.log('Админка инициализируется...');
    
    // Проверяем, авторизован ли админ
    const isLoggedIn = localStorage.getItem('jetStoreAdminLoggedIn') === 'true';
    console.log('Статус входа:', isLoggedIn);
    
    if (isLoggedIn) {
        showAdminPanel();
    } else {
        showLoginPanel();
    }
    
    // Настройка обработчиков событий
    setupEventListeners();
    
    // Загрузка начальных данных
    loadInitialData();
    
    console.log('Админка готова');
}

// Настройка обработчиков событий
function setupEventListeners() {
    console.log('Настройка обработчиков событий...');
    
    // Форма входа
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const password = document.getElementById('adminPassword').value;
            console.log('Попытка входа с паролем:', password);
            login(password);
        });
    }
    
    // Форма товара
    const productForm = document.getElementById('productForm');
    if (productForm) {
        productForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveProduct();
        });
    }
    
    // Форма пользователя
    const userForm = document.getElementById('userForm');
    if (userForm) {
        userForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveUser();
        });
    }
    
    // Форма пароля
    const passwordForm = document.getElementById('passwordForm');
    if (passwordForm) {
        passwordForm.addEventListener('submit', function(e) {
            e.preventDefault();
            changePassword();
        });
    }
    
    // Обработчик для импорта файлов
    const importFile = document.getElementById('importFile');
    if (importFile) {
        importFile.addEventListener('change', function(e) {
            importDataFile(e.target.files[0]);
        });
    }
    
    console.log('Обработчики настроены');
}

// Показать панель входа
function showLoginPanel() {
    console.log('Показываем панель входа');
    const loginContainer = document.getElementById('loginContainer');
    const adminPanel = document.getElementById('adminPanel');
    
    if (loginContainer) loginContainer.style.display = 'block';
    if (adminPanel) adminPanel.style.display = 'none';
}

// Показать админ-панель
function showAdminPanel() {
    console.log('Показываем админ-панель');
    const loginContainer = document.getElementById('loginContainer');
    const adminPanel = document.getElementById('adminPanel');
    
    if (loginContainer) loginContainer.style.display = 'none';
    if (adminPanel) adminPanel.style.display = 'block';
    
    // Обновляем статистику
    refreshStatistics();
}

// Вход в админку
function login(password) {
    console.log('Попытка входа...');
    console.log('Введен пароль:', password);
    
    // Проверяем доступ к Database
    if (typeof Database === 'undefined') {
        console.error('Database не загружен!');
        showNotification('Ошибка: база данных не загружена', 'error');
        return;
    }
    
    console.log('Проверяем пароль...');
    const isCorrect = Database.checkAdminPassword(password);
    console.log('Пароль правильный?', isCorrect);
    
    if (isCorrect) {
        localStorage.setItem('jetStoreAdminLoggedIn', 'true');
        showAdminPanel();
        showNotification('Успешный вход в админ-панель', 'success');
        
        // Переключаемся на раздел статистики
        showAdminSection('stats');
    } else {
        showNotification('Неверный пароль администратора', 'error');
        // Показываем правильный пароль для отладки
        const settings = Database.getAdminSettings();
        console.log('Текущий пароль в настройках:', settings.password);
    }
}

// Выход из админки
function logout() {
    localStorage.removeItem('jetStoreAdminLoggedIn');
    showLoginPanel();
    const adminPasswordInput = document.getElementById('adminPassword');
    if (adminPasswordInput) adminPasswordInput.value = '';
}

// Показать раздел админки
function showAdminSection(section) {
    console.log('Переключаемся на раздел:', section);
    
    // Скрыть все разделы
    document.querySelectorAll('.admin-content').forEach(el => {
        el.classList.remove('active');
    });
    
    // Убрать активный класс у всех кнопок
    document.querySelectorAll('.admin-nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Показать выбранный раздел
    const sectionElement = document.getElementById(section + 'Section');
    if (sectionElement) {
        sectionElement.classList.add('active');
    }
    
    // Активировать соответствующую кнопку
    const activeBtn = document.querySelector(`.admin-nav-btn[onclick*="${section}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // Загрузить данные раздела
    currentAdminSection = section;
    
    if (section === 'products') {
        loadProducts(currentCategory);
    } else if (section === 'users') {
        loadUsers();
    } else if (section === 'settings') {
        loadSettings();
    }
}

// Показать категорию товаров
function showCategory(category) {
    console.log('Показываем категорию:', category);
    currentCategory = category;
    
    // Убрать активный класс у всех вкладок
    document.querySelectorAll('.category-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Активировать выбранную вкладку
    const activeTab = document.querySelector(`.category-tab[onclick*="${category}"]`);
    if (activeTab) {
        activeTab.classList.add('active');
    }
    
    // Загрузить товары категории
    loadProducts(category);
}

// Загрузка начальных данных
function loadInitialData() {
    console.log('Загружаем начальные данные...');
    
    // Загружаем курсы валют
    const db = window.Database || Database;
    if (db && typeof db.getCurrencyRates === 'function') {
        const rates = db.getCurrencyRates();
        
        const usdtRateEl = document.getElementById('usdtRate');
        const usdRateEl = document.getElementById('usdRate');
        const eurRateEl = document.getElementById('eurRate');
        const usdtInput = document.getElementById('usdtInput');
        const usdInput = document.getElementById('usdInput');
        const eurInput = document.getElementById('eurInput');
        
        if (usdtRateEl) usdtRateEl.textContent = rates.USDT || 80;
        if (usdRateEl) usdRateEl.textContent = rates.USD || 90;
        if (eurRateEl) eurRateEl.textContent = rates.EUR || 100;
        if (usdtInput) usdtInput.value = rates.USDT || 80;
        if (usdInput) usdInput.value = rates.USD || 90;
        if (eurInput) eurInput.value = rates.EUR || 100;
    }
    
    // Загружаем товары текущей категории
    loadProducts(currentCategory);
    
    // Загружаем пользователей
    loadUsers();
    
    // Загружаем настройки
    loadSettings();
    
    // Загружаем товары Supercell
    loadSupercellProducts(currentSupercellCategory);
    
    // Обновляем статистику
    refreshStatistics();
    
    console.log('Начальные данные загружены');
}

// Обновление статистики
function refreshStatistics() {
    console.log('Обновляем статистику...');
    
    if (typeof Database !== 'undefined') {
        const stats = Database.getStatistics();
        
        const statUsers = document.getElementById('statUsers');
        const statProducts = document.getElementById('statProducts');
        const statBalance = document.getElementById('statBalance');
        const statUpdated = document.getElementById('statUpdated');
        
        if (statUsers) statUsers.textContent = stats.totalUsers;
        if (statProducts) statProducts.textContent = stats.totalProducts;
        if (statBalance) statBalance.textContent = stats.totalBalance + ' ₽';
        if (statUpdated) statUpdated.textContent = stats.lastUpdated;
        
        showNotification('Статистика обновлена', 'success');
    }
}

// Загрузка товаров
function loadProducts(category) {
    console.log('Загружаем товары категории:', category);
    
    if (typeof Database !== 'undefined') {
        const products = Database.getProductsByCategory(category);
        const productsList = document.getElementById('productsList');
        
        if (!productsList) {
            console.error('Не найден элемент productsList');
            return;
        }
        
        if (products.length === 0) {
            productsList.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-box-open" style="font-size: 3rem; margin-bottom: 15px; color: #667eea;"></i>
                    <p>В этой категории пока нет товаров</p>
                </div>
            `;
            return;
        }
        
        productsList.innerHTML = products.map(product => `
            <div class="product-item">
                <div class="product-info">
                    <div class="product-title">${product.name || 'Без названия'}</div>
                    <div>${product.description || 'Без описания'}</div>
                    <div class="product-price">${product.price || 0} звёзд</div>
                </div>
                <div class="product-actions">
                    <button class="action-btn edit" onclick="editProduct('${category}', '${product.id}')">
                        <i class="fas fa-edit"></i> Изменить
                    </button>
                    <button class="action-btn delete" onclick="deleteProduct('${category}', '${product.id}')">
                        <i class="fas fa-trash"></i> Удалить
                    </button>
                </div>
            </div>
        `).join('');
    }
}

// Сброс формы товара
function resetProductForm() {
    const form = document.getElementById('productForm');
    if (form) form.reset();
    
    const productId = document.getElementById('productId');
    if (productId) productId.value = '';
    
    const productCategory = document.getElementById('productCategory');
    if (productCategory) productCategory.value = currentCategory;
    
    currentEditingProduct = null;
    
    // Устанавливаем категорию по умолчанию
    const badgeField = document.getElementById('productBadge');
    if (badgeField) {
        const badgeMap = {
            'telegram': 'Telegram',
            'steam': 'Steam',
            'games': 'Игры',
            'brawlstars': 'Brawl Stars',
            'clashroyale': 'Clash Royale',
            'clashofclans': 'Clash of Clans',
            'standoff2': 'Standoff 2',
            'pubgmobile': 'PUBG Mobile'
        };
        badgeField.value = badgeMap[currentCategory] || 'Товар';
    }
    
    const iconField = document.getElementById('productIcon');
    if (iconField) {
        const iconMap = {
            'telegram': 'fab fa-telegram',
            'steam': 'fab fa-steam',
            'games': 'fas fa-gamepad',
            'brawlstars': 'fas fa-star',
            'clashroyale': 'fas fa-crown',
            'clashofclans': 'fas fa-shield-alt',
            'standoff2': 'fas fa-crosshairs',
            'pubgmobile': 'fas fa-crosshairs'
        };
        iconField.value = iconMap[currentCategory] || 'fas fa-box';
    }
}

// Редактировать товар
function editProduct(category, productId) {
    console.log('Редактируем товар:', productId, 'в категории:', category);
    
    if (typeof Database !== 'undefined') {
        const products = Database.getProductsByCategory(category);
        const product = products.find(p => p.id === productId);
        
        if (product) {
            currentEditingProduct = product;
            currentCategory = category;
            
            // Заполняем форму
            const productIdField = document.getElementById('productId');
            const productCategoryField = document.getElementById('productCategory');
            const productNameField = document.getElementById('productName');
            const productPriceField = document.getElementById('productPrice');
            const productIconField = document.getElementById('productIcon');
            const productBadgeField = document.getElementById('productBadge');
            const productDescriptionField = document.getElementById('productDescription');
            const productDetailsField = document.getElementById('productDetails');
            
            if (productIdField) productIdField.value = product.id;
            if (productCategoryField) productCategoryField.value = category;
            if (productNameField) productNameField.value = product.name || '';
            if (productPriceField) productPriceField.value = product.price || '';
            if (productIconField) productIconField.value = product.icon || '';
            if (productBadgeField) productBadgeField.value = product.badge || '';
            if (productDescriptionField) productDescriptionField.value = product.description || '';
            if (productDetailsField) productDetailsField.value = product.details || '';
            
            // Показываем раздел товаров
            showAdminSection('products');
            
            showNotification('Товар загружен для редактирования', 'success');
        }
    }
}

// Сохранить товар
function saveProduct() {
    console.log('Сохраняем товар...');
    
    if (typeof Database !== 'undefined') {
        const productId = document.getElementById('productId')?.value;
        const category = document.getElementById('productCategory')?.value || currentCategory;
        
        const productData = {
            name: document.getElementById('productName')?.value || 'Новый товар',
            price: parseFloat(document.getElementById('productPrice')?.value) || 0,
            icon: document.getElementById('productIcon')?.value || 'fas fa-box',
            badge: document.getElementById('productBadge')?.value || 'Товар',
            description: document.getElementById('productDescription')?.value || 'Описание товара',
            details: document.getElementById('productDetails')?.value || ''
        };
        
        console.log('Данные товара:', productData);
        console.log('ID товара:', productId);
        console.log('Категория:', category);
        
        let success = false;
        let message = '';
        
        if (productId) {
            // Обновление существующего товара
            success = Database.updateProduct(category, productId, productData);
            message = success ? 'Товар успешно обновлен' : 'Ошибка обновления товара';
        } else {
            // Добавление нового товара
            const newProduct = Database.addProduct(category, productData);
            success = !!newProduct;
            message = success ? 'Товар успешно добавлен' : 'Ошибка добавления товара';
        }
        
        if (success) {
            showNotification(message, 'success');
            resetProductForm();
            loadProducts(category);
            
            // Обновляем статистику
            refreshStatistics();
        } else {
            showNotification(message, 'error');
        }
    }
}

// Удалить товар
function deleteProduct(category, productId) {
    console.log('Удаляем товар:', productId, 'из категории:', category);
    
    if (confirm('Вы уверены, что хотите удалить этот товар?')) {
        if (typeof Database !== 'undefined') {
            const success = Database.deleteProduct(category, productId);
            
            if (success) {
                showNotification('Товар успешно удален', 'success');
                loadProducts(category);
                refreshStatistics();
            } else {
                showNotification('Ошибка удаления товара', 'error');
            }
        }
    }
}

// Загрузка пользователей
function loadUsers() {
    console.log('Загружаем пользователей...');
    
    if (typeof Database !== 'undefined') {
        const users = Database.getUsers();
        const usersTableBody = document.getElementById('usersTableBody');
        
        if (!usersTableBody) {
            console.error('Не найден элемент usersTableBody');
            return;
        }
        
        if (Object.keys(users).length === 0) {
            usersTableBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-user-slash" style="font-size: 2rem; margin-bottom: 10px; color: #667eea;"></i>
                        <p>Пользователи не найдены</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        usersTableBody.innerHTML = Object.values(users).map(user => `
            <tr>
                <td>${user.id || '-'}</td>
                <td>${user.firstName || 'Не указано'}</td>
                <td>${user.username ? '@' + user.username : '-'}</td>
                <td>${user.language || 'ru'}</td>
                <td>${user.currencies?.RUB || 0} ₽</td>
                <td>
                    <button class="action-btn edit" onclick="editUser('${user.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }
}

// Редактировать пользователя
function editUser(userId) {
    console.log('Редактируем пользователя:', userId);
    
    if (typeof Database !== 'undefined') {
        const user = Database.getUser(userId);
        
        if (user) {
            currentEditingUser = user;
            
            // Заполняем форму
            const userIdField = document.getElementById('userId');
            const userNameField = document.getElementById('userName');
            const userLanguageField = document.getElementById('userLanguage');
            const userBalanceField = document.getElementById('userBalance');
            const userBalanceUSDField = document.getElementById('userBalanceUSD');
            
            if (userIdField) userIdField.value = user.id;
            if (userNameField) userNameField.value = user.firstName || user.username || 'Пользователь';
            if (userLanguageField) userLanguageField.value = user.language || 'ru';
            if (userBalanceField) userBalanceField.value = user.currencies?.RUB || 0;
            if (userBalanceUSDField) userBalanceUSDField.value = user.currencies?.USDT || 0;
            
            // Показываем раздел пользователей
            showAdminSection('users');
            
            showNotification('Данные пользователя загружены', 'success');
        }
    }
}

// Сохранить пользователя
function saveUser() {
    console.log('Сохраняем пользователя...');
    
    if (typeof Database !== 'undefined') {
        const userId = document.getElementById('userId')?.value;
        const user = Database.getUser(userId);
        
        if (user) {
            const updates = {
                language: document.getElementById('userLanguage')?.value || 'ru',
                currencies: {
                    RUB: parseFloat(document.getElementById('userBalance')?.value) || 0,
                    USDT: parseFloat(document.getElementById('userBalanceUSD')?.value) || 0,
                    USD: 0,
                    EUR: 0
                }
            };
            
            console.log('Обновления пользователя:', updates);
            
            // Обновляем пользователя
            const updatedUser = { ...user, ...updates };
            Database.saveUser(updatedUser);
            
            showNotification('Данные пользователя обновлены', 'success');
            loadUsers();
            refreshStatistics();
        }
    }
}

// Сброс формы пользователя
function resetUserForm() {
    const form = document.getElementById('userForm');
    if (form) form.reset();
    
    const userIdField = document.getElementById('userId');
    if (userIdField) userIdField.value = '';
    
    currentEditingUser = null;
}

// Изменение пароля
function changePassword() {
    console.log('Изменяем пароль...');
    
    if (typeof Database !== 'undefined') {
        const currentPassword = document.getElementById('currentPassword')?.value;
        const newPassword = document.getElementById('newPassword')?.value;
        const confirmPassword = document.getElementById('confirmPassword')?.value;
        
        // Проверка текущего пароля
        if (!Database.checkAdminPassword(currentPassword)) {
            showNotification('Текущий пароль неверен', 'error');
            return;
        }
        
        // Проверка совпадения новых паролей
        if (newPassword !== confirmPassword) {
            showNotification('Новые пароли не совпадают', 'error');
            return;
        }
        
        // Проверка длины пароля
        if (newPassword.length < 4) {
            showNotification('Пароль должен быть не менее 4 символов', 'error');
            return;
        }
        
        // Изменение пароля
        Database.changeAdminPassword(newPassword);
        
        showNotification('Пароль успешно изменен', 'success');
        
        const form = document.getElementById('passwordForm');
        if (form) form.reset();
    }
}

// Сохранение курсов валют
function saveCurrencyRates() {
    console.log('Сохраняем курсы валют...');
    
    const db = window.Database || Database;
    if (db && typeof db.updateCurrencyRates === 'function') {
        const rates = {
            RUB: 1,
            USDT: parseFloat(document.getElementById('usdtInput')?.value) || 80,
            USD: parseFloat(document.getElementById('usdInput')?.value) || 90,
            EUR: parseFloat(document.getElementById('eurInput')?.value) || 100
        };
        
        console.log('Новые курсы валют:', rates);
        
        db.updateCurrencyRates(rates);
        
        // Обновляем отображение
        const usdtRateEl = document.getElementById('usdtRate');
        const usdRateEl = document.getElementById('usdRate');
        const eurRateEl = document.getElementById('eurRate');
        
        if (usdtRateEl) usdtRateEl.textContent = rates.USDT;
        if (usdRateEl) usdRateEl.textContent = rates.USD;
        if (eurRateEl) eurRateEl.textContent = rates.EUR;
        
        showNotification('Курсы валют обновлены', 'success');
    } else {
        showNotification('Ошибка: Database недоступна', 'error');
    }
}

// Сохранение курса 1 звезды
function saveStarRate() {
    console.log('Сохраняем курс 1 звезды...');
    
    const starRate = parseFloat(document.getElementById('starRateInput')?.value) || 1.37;
    
    try {
        localStorage.setItem('jetstore_star_rate', starRate.toString());
        showNotification('Курс 1 звезды сохранён', 'success');
        console.log('Курс 1 звезды сохранён:', starRate);
        
        // Обновляем отображение
        const starRateEl = document.getElementById('starRate');
        if (starRateEl) starRateEl.textContent = starRate;
    } catch (error) {
        console.error('Ошибка сохранения курса 1 звезды:', error);
        showNotification('Ошибка сохранения курса', 'error');
    }
}

// Сохранение курса скупки 1 звезды
function saveStarBuyRate() {
    console.log('Сохраняем курс скупки 1 звезды...');
    
    const buyRate = parseFloat(document.getElementById('starBuyRateInput')?.value) || 0.65;
    
    try {
        localStorage.setItem('jetstore_star_buy_rate', buyRate.toString());
        showNotification('Курс скупки 1 звезды сохранён', 'success');
        console.log('Курс скупки 1 звезды сохранён:', buyRate);
        
        const starBuyRateEl = document.getElementById('starBuyRate');
        if (starBuyRateEl) starBuyRateEl.textContent = buyRate;
    } catch (error) {
        console.error('Ошибка сохранения курса скупки 1 звезды:', error);
        showNotification('Ошибка сохранения курса скупки', 'error');
    }
}

// Сохранение цен на звёзды
function saveStarsPrices() {
    console.log('Сохраняем цены на звёзды...');
    
    // Сначала сохраняем курс 1 звезды
    saveStarRate();
    
    const prices = {
        50: parseFloat(document.getElementById('starsPrice50')?.value) || 69,
        100: parseFloat(document.getElementById('starsPrice100')?.value) || 137,
        250: parseFloat(document.getElementById('starsPrice250')?.value) || 343,
        500: parseFloat(document.getElementById('starsPrice500')?.value) || 685,
        1000: parseFloat(document.getElementById('starsPrice1000')?.value) || 1370
    };
    
    try {
        localStorage.setItem('jetstore_stars_prices', JSON.stringify(prices));
        showNotification('Цены на звёзды сохранены', 'success');
        console.log('Цены на звёзды сохранены:', prices);
    } catch (error) {
        console.error('Ошибка сохранения цен на звёзды:', error);
        showNotification('Ошибка сохранения цен', 'error');
    }
}

// Сохранение цен на Premium
function savePremiumPrices() {
    console.log('Сохраняем цены на Premium...');
    
    const prices = {
        3: parseFloat(document.getElementById('premiumPrice3')?.value) || 983,
        6: parseFloat(document.getElementById('premiumPrice6')?.value) || 1311,
        12: parseFloat(document.getElementById('premiumPrice12')?.value) || 2377
    };
    
    try {
        localStorage.setItem('jetstore_premium_prices', JSON.stringify(prices));
        showNotification('Цены на Premium сохранены', 'success');
        console.log('Цены на Premium сохранены:', prices);
    } catch (error) {
        console.error('Ошибка сохранения цен на Premium:', error);
        showNotification('Ошибка сохранения цен', 'error');
    }
}

// Загрузка настроек
function loadSettings() {
    console.log('Загружаем настройки...');
    
    const db = window.Database || Database;
    if (db && typeof db.getCurrencyRates === 'function') {
        const rates = db.getCurrencyRates();
        
        const usdtInput = document.getElementById('usdtInput');
        const usdInput = document.getElementById('usdInput');
        const eurInput = document.getElementById('eurInput');
        
        const usdtRateEl = document.getElementById('usdtRate');
        const usdRateEl = document.getElementById('usdRate');
        const eurRateEl = document.getElementById('eurRate');
        
        if (usdtInput) usdtInput.value = rates.USDT || 80;
        if (usdInput) usdInput.value = rates.USD || 90;
        if (eurInput) eurInput.value = rates.EUR || 100;
        
        if (usdtRateEl) usdtRateEl.textContent = rates.USDT || 80;
        if (usdRateEl) usdRateEl.textContent = rates.USD || 90;
        if (eurRateEl) eurRateEl.textContent = rates.EUR || 100;
    }
    
    // Загружаем курс скупки звезды
    try {
        const buyRate = parseFloat(localStorage.getItem('jetstore_star_buy_rate') || '0.65');
        const buyRateDisplay = document.getElementById('starBuyRate');
        const buyRateInput = document.getElementById('starBuyRateInput');
        if (buyRateDisplay) buyRateDisplay.textContent = buyRate;
        if (buyRateInput) buyRateInput.value = buyRate;
    } catch (error) {
        console.error('Ошибка загрузки курса скупки звезды:', error);
    }
    
    // Загружаем цены на звёзды
    try {
        const starsPrices = JSON.parse(localStorage.getItem('jetstore_stars_prices') || '{}');
        const defaultStarsPrices = { 50: 69, 100: 137, 250: 343, 500: 685, 1000: 1370 };
        const finalStarsPrices = { ...defaultStarsPrices, ...starsPrices };
        
        if (document.getElementById('starsPrice50')) document.getElementById('starsPrice50').value = finalStarsPrices[50];
        if (document.getElementById('starsPrice100')) document.getElementById('starsPrice100').value = finalStarsPrices[100];
        if (document.getElementById('starsPrice250')) document.getElementById('starsPrice250').value = finalStarsPrices[250];
        if (document.getElementById('starsPrice500')) document.getElementById('starsPrice500').value = finalStarsPrices[500];
        if (document.getElementById('starsPrice1000')) document.getElementById('starsPrice1000').value = finalStarsPrices[1000];
    } catch (error) {
        console.error('Ошибка загрузки цен на звёзды:', error);
    }
    
    // Загружаем цены на Premium
    try {
        const premiumPrices = JSON.parse(localStorage.getItem('jetstore_premium_prices') || '{}');
        const defaultPremiumPrices = { 3: 983, 6: 1311, 12: 2377 };
        const finalPremiumPrices = { ...defaultPremiumPrices, ...premiumPrices };
        
        if (document.getElementById('premiumPrice3')) document.getElementById('premiumPrice3').value = finalPremiumPrices[3];
        if (document.getElementById('premiumPrice6')) document.getElementById('premiumPrice6').value = finalPremiumPrices[6];
        if (document.getElementById('premiumPrice12')) document.getElementById('premiumPrice12').value = finalPremiumPrices[12];
    } catch (error) {
        console.error('Ошибка загрузки цен на Premium:', error);
    }
}

// Экспорт данных
function exportData() {
    console.log('Экспортируем данные...');
    
    if (typeof Database !== 'undefined') {
        const data = {
            products: Database.getProducts(),
            users: Database.getUsers(),
            settings: Database.getAdminSettings(),
            exportDate: new Date().toISOString(),
            version: '1.0'
        };
        
        const dataStr = JSON.stringify(data, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `jetstore_backup_${new Date().toISOString().split('T')[0]}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        document.body.appendChild(linkElement);
        linkElement.click();
        document.body.removeChild(linkElement);
        
        showNotification('Данные успешно экспортированы', 'success');
    }
}

// Импорт данных
function importData() {
    console.log('Инициируем импорт данных...');
    document.getElementById('importFile').click();
}

// Импорт данных из файла
function importDataFile(file) {
    console.log('Импортируем данные из файла:', file?.name);
    
    if (!file) return;
    
    if (confirm('ВНИМАНИЕ: Импорт данных перезапишет текущие данные. Продолжить?')) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                
                // Проверяем структуру данных
                if (data.products && data.users && data.settings) {
                    // Сохраняем данные
                    localStorage.setItem('jetStoreProducts', JSON.stringify(data.products));
                    localStorage.setItem('jetStoreUsers', JSON.stringify(data.users));
                    localStorage.setItem('jetStoreAdminSettings', JSON.stringify(data.settings));
                    
                    showNotification('Данные успешно импортированы', 'success');
                    
                    // Обновляем отображение
                    if (currentAdminSection === 'products') {
                        loadProducts(currentCategory);
                    } else if (currentAdminSection === 'users') {
                        loadUsers();
                    } else if (currentAdminSection === 'settings') {
                        loadSettings();
                    }
                    
                    refreshStatistics();
                } else {
                    showNotification('Неверный формат файла данных', 'error');
                }
            } catch (error) {
                console.error('Ошибка импорта:', error);
                showNotification('Ошибка при чтении файла: ' + error.message, 'error');
            }
        };
        
        reader.readAsText(file);
    }
}

// Сброс всех данных
function resetData() {
    if (confirm('ВНИМАНИЕ: Это удалит ВСЕ данные (товары, пользователей, настройки). Действие необратимо. Продолжить?')) {
        // Сбрасываем базу данных
        localStorage.removeItem('jetStoreProducts');
        localStorage.removeItem('jetStoreUsers');
        localStorage.removeItem('jetStoreAdminSettings');
        localStorage.removeItem('jetStoreAdminLoggedIn');
        
        // Инициализируем заново
        if (typeof Database !== 'undefined') {
            Database.init();
        }
        
        // Сбрасываем формы
        resetProductForm();
        resetUserForm();
        
        // Обновляем отображение
        loadProducts(currentCategory);
        loadUsers();
        loadSettings();
        refreshStatistics();
        
        showNotification('Все данные сброшены', 'success');
    }
}

// Показать уведомление
function showNotification(message, type = 'info') {
    console.log('Уведомление:', message, type);
    
    // Удаляем старое уведомление
    const oldNotification = document.querySelector('.notification');
    if (oldNotification) {
        oldNotification.remove();
    }
    
    // Создаем новое уведомление
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Автоматическое удаление через 3 секунды
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 3000);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM загружен, инициализируем админку...');
    
    // Даем немного времени на загрузку всех скриптов
    setTimeout(initAdmin, 100);
});

// Управление товарами Supercell
let currentSupercellCategory = 'clashroyale';

function switchSupercellCategory(game) {
    currentSupercellCategory = game;
    document.querySelectorAll('.category-tab').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.includes(game === 'clashroyale' ? 'Clash Royale' : game === 'clashofclans' ? 'Clash of Clans' : 'Brawl Stars')) {
            btn.classList.add('active');
        }
    });
    loadSupercellProducts(game);
}

function loadSupercellProducts(game) {
    const container = document.getElementById('supercellProductsAdmin');
    if (!container) return;
    
    try {
        const productsKey = `jetstore_supercell_${game}`;
        let products = JSON.parse(localStorage.getItem(productsKey) || '[]');
        
        // Инициализация товаров по умолчанию, если их нет
        if (products.length === 0) {
            const defaultProducts = {
                'clashroyale': [{ name: 'Royal Pass', price: 299 }],
                'clashofclans': [{ name: 'Pass', price: 299 }],
                'brawlstars': [{ name: 'Brawl Pass', price: 299 }]
            };
            if (defaultProducts[game]) {
                products = defaultProducts[game];
                localStorage.setItem(productsKey, JSON.stringify(products));
            }
        }
        
        container.innerHTML = '';
        
        if (products.length === 0) {
            container.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">Товары пока не добавлены</p>';
            return;
        }
        
        products.forEach((product, index) => {
            const item = document.createElement('div');
            item.className = 'product-item';
            item.innerHTML = `
                <div class="product-info">
                    <div class="product-title">${product.name || 'Товар'}</div>
                    <div class="product-price">${product.price || 0} ₽</div>
                </div>
                <div class="product-actions">
                    <button class="action-btn edit" onclick="editSupercellProduct('${game}', ${index})">
                        <i class="fas fa-edit"></i> Изменить
                    </button>
                    <button class="action-btn delete" onclick="deleteSupercellProduct('${game}', ${index})">
                        <i class="fas fa-trash"></i> Удалить
                    </button>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Ошибка загрузки товаров Supercell:', error);
        container.innerHTML = '<p style="color: #f44336; text-align: center; padding: 20px;">Ошибка загрузки товаров</p>';
    }
}

function addSupercellProduct() {
    const name = document.getElementById('newSupercellProductName')?.value.trim();
    const price = parseFloat(document.getElementById('newSupercellProductPrice')?.value) || 0;
    
    if (!name) {
        showNotification('Введите название товара', 'error');
        return;
    }
    
    if (price <= 0) {
        showNotification('Введите корректную цену', 'error');
        return;
    }
    
    try {
        const productsKey = `jetstore_supercell_${currentSupercellCategory}`;
        const products = JSON.parse(localStorage.getItem(productsKey) || '[]');
        
        products.push({ name, price });
        localStorage.setItem(productsKey, JSON.stringify(products));
        
        document.getElementById('newSupercellProductName').value = '';
        document.getElementById('newSupercellProductPrice').value = '';
        
        loadSupercellProducts(currentSupercellCategory);
        showNotification('Товар добавлен', 'success');
    } catch (error) {
        console.error('Ошибка добавления товара:', error);
        showNotification('Ошибка при добавлении товара', 'error');
    }
}

function editSupercellProduct(game, index) {
    try {
        const productsKey = `jetstore_supercell_${game}`;
        const products = JSON.parse(localStorage.getItem(productsKey) || '[]');
        const product = products[index];
        
        if (!product) {
            showNotification('Товар не найден', 'error');
            return;
        }
        
        const newName = prompt('Введите новое название:', product.name);
        if (newName === null) return;
        
        const newPrice = parseFloat(prompt('Введите новую цену (₽):', product.price));
        if (isNaN(newPrice) || newPrice <= 0) {
            showNotification('Неверная цена', 'error');
            return;
        }
        
        products[index] = { name: newName.trim(), price: newPrice };
        localStorage.setItem(productsKey, JSON.stringify(products));
        
        loadSupercellProducts(game);
        showNotification('Товар изменён', 'success');
    } catch (error) {
        console.error('Ошибка редактирования товара:', error);
        showNotification('Ошибка при изменении товара', 'error');
    }
}

function deleteSupercellProduct(game, index) {
    if (!confirm('Удалить этот товар?')) return;
    
    try {
        const productsKey = `jetstore_supercell_${game}`;
        const products = JSON.parse(localStorage.getItem(productsKey) || '[]');
        
        products.splice(index, 1);
        localStorage.setItem(productsKey, JSON.stringify(products));
        
        loadSupercellProducts(game);
        showNotification('Товар удалён', 'success');
    } catch (error) {
        console.error('Ошибка удаления товара:', error);
        showNotification('Ошибка при удалении товара', 'error');
    }
}


// =============================================
// Управление Usernames
// =============================================
function loadUsernamesAdmin() {
    const container = document.getElementById('usernamesAdminList');
    if (!container) return;
    
    try {
        const usernames = JSON.parse(localStorage.getItem('jetstore_usernames') || '[]');
        
        if (usernames.length === 0) {
            container.innerHTML = '<p style="color: #666; text-align: center; padding: 30px;">Usernames пока не добавлены</p>';
            return;
        }
        
        container.innerHTML = usernames.map((u, index) => `
            <div class="product-item">
                <div class="product-info">
                    <div class="product-title">@${u.username}</div>
                    <div style="color: #00d4ff; font-weight: 600;">${u.price} TON</div>
                    <div style="color: #888; font-size: 0.9rem;">${u.status === 'for_sale' ? 'На продаже' : 'На аукционе'} | ${u.timeLeft || 'Без ограничений'}</div>
                </div>
                <div class="product-actions">
                    <button class="action-btn edit" onclick="editUsername(${index})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn delete" onclick="deleteUsername(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Ошибка загрузки usernames:', error);
        container.innerHTML = '<p style="color: #f44336; text-align: center; padding: 20px;">Ошибка загрузки</p>';
    }
}

function addUsername() {
    const username = document.getElementById('newUsernameInput')?.value.trim();
    const price = parseInt(document.getElementById('newUsernamePrice')?.value) || 0;
    const status = document.getElementById('newUsernameStatus')?.value || 'for_sale';
    const timeLeft = document.getElementById('newUsernameTime')?.value.trim() || '';
    
    if (!username) {
        showNotification('Введите username', 'error');
        return;
    }
    
    if (price <= 0) {
        showNotification('Введите корректную цену', 'error');
        return;
    }
    
    try {
        const usernames = JSON.parse(localStorage.getItem('jetstore_usernames') || '[]');
        
        usernames.push({
            username: username.replace('@', ''),
            price: price,
            status: status,
            timeLeft: timeLeft
        });
        
        localStorage.setItem('jetstore_usernames', JSON.stringify(usernames));
        
        // Очищаем поля
        document.getElementById('newUsernameInput').value = '';
        document.getElementById('newUsernamePrice').value = '';
        document.getElementById('newUsernameTime').value = '';
        
        loadUsernamesAdmin();
        showNotification('Username добавлен', 'success');
    } catch (error) {
        console.error('Ошибка добавления username:', error);
        showNotification('Ошибка при добавлении', 'error');
    }
}

function editUsername(index) {
    try {
        const usernames = JSON.parse(localStorage.getItem('jetstore_usernames') || '[]');
        const u = usernames[index];
        
        if (!u) {
            showNotification('Username не найден', 'error');
            return;
        }
        
        const newUsername = prompt('Введите новый username:', u.username);
        if (newUsername === null) return;
        
        const newPrice = parseInt(prompt('Введите новую цену (TON):', u.price));
        if (isNaN(newPrice) || newPrice <= 0) {
            showNotification('Неверная цена', 'error');
            return;
        }
        
        const newStatus = prompt('Статус (for_sale или on_auction):', u.status);
        const newTime = prompt('Время (осталось):', u.timeLeft || '');
        
        usernames[index] = {
            username: newUsername.replace('@', '').trim(),
            price: newPrice,
            status: newStatus === 'on_auction' ? 'on_auction' : 'for_sale',
            timeLeft: newTime || ''
        };
        
        localStorage.setItem('jetstore_usernames', JSON.stringify(usernames));
        loadUsernamesAdmin();
        showNotification('Username изменён', 'success');
    } catch (error) {
        console.error('Ошибка редактирования username:', error);
        showNotification('Ошибка при изменении', 'error');
    }
}

function deleteUsername(index) {
    if (!confirm('Удалить этот username?')) return;
    
    try {
        const usernames = JSON.parse(localStorage.getItem('jetstore_usernames') || '[]');
        usernames.splice(index, 1);
        localStorage.setItem('jetstore_usernames', JSON.stringify(usernames));
        
        loadUsernamesAdmin();
        showNotification('Username удалён', 'success');
    } catch (error) {
        console.error('Ошибка удаления username:', error);
        showNotification('Ошибка при удалении', 'error');
    }
}

// =============================================
// Управление Номерами +888
// =============================================
function loadNumbersAdmin() {
    const container = document.getElementById('numbersAdminList');
    if (!container) return;
    
    try {
        const numbers = JSON.parse(localStorage.getItem('jetstore_numbers') || '[]');
        
        if (numbers.length === 0) {
            container.innerHTML = '<p style="color: #666; text-align: center; padding: 30px;">Номера пока не добавлены</p>';
            return;
        }
        
        container.innerHTML = numbers.map((n, index) => `
            <div class="product-item">
                <div class="product-info">
                    <div class="product-title">${n.number}</div>
                    <div style="color: #00d4ff; font-weight: 600;">${n.minBid.toLocaleString('ru-RU')} TON</div>
                    <div style="color: #888; font-size: 0.9rem;">${n.status === 'on_auction' ? 'На аукционе' : 'На продаже'} | ${n.type || 'Resale'} | ${n.auctionEnds || 'Без ограничений'}</div>
                </div>
                <div class="product-actions">
                    <button class="action-btn edit" onclick="editNumber(${index})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn delete" onclick="deleteNumber(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Ошибка загрузки номеров:', error);
        container.innerHTML = '<p style="color: #f44336; text-align: center; padding: 20px;">Ошибка загрузки</p>';
    }
}

function addNumber() {
    const number = document.getElementById('newNumberInput')?.value.trim();
    const minBid = parseInt(document.getElementById('newNumberBid')?.value) || 0;
    const status = document.getElementById('newNumberStatus')?.value || 'on_auction';
    const type = document.getElementById('newNumberType')?.value.trim() || 'Resale';
    const auctionEnds = document.getElementById('newNumberEnds')?.value.trim() || '';
    
    if (!number) {
        showNotification('Введите номер телефона', 'error');
        return;
    }
    
    if (minBid <= 0) {
        showNotification('Введите корректную ставку', 'error');
        return;
    }
    
    try {
        const numbers = JSON.parse(localStorage.getItem('jetstore_numbers') || '[]');
        
        numbers.push({
            number: number,
            minBid: minBid,
            status: status,
            type: type,
            auctionEnds: auctionEnds
        });
        
        localStorage.setItem('jetstore_numbers', JSON.stringify(numbers));
        
        // Очищаем поля
        document.getElementById('newNumberInput').value = '';
        document.getElementById('newNumberBid').value = '';
        document.getElementById('newNumberType').value = '';
        document.getElementById('newNumberEnds').value = '';
        
        loadNumbersAdmin();
        showNotification('Номер добавлен', 'success');
    } catch (error) {
        console.error('Ошибка добавления номера:', error);
        showNotification('Ошибка при добавлении', 'error');
    }
}

function editNumber(index) {
    try {
        const numbers = JSON.parse(localStorage.getItem('jetstore_numbers') || '[]');
        const n = numbers[index];
        
        if (!n) {
            showNotification('Номер не найден', 'error');
            return;
        }
        
        const newNumber = prompt('Введите новый номер:', n.number);
        if (newNumber === null) return;
        
        const newBid = parseInt(prompt('Введите минимальную ставку (TON):', n.minBid));
        if (isNaN(newBid) || newBid <= 0) {
            showNotification('Неверная ставка', 'error');
            return;
        }
        
        const newStatus = prompt('Статус (on_auction или for_sale):', n.status);
        const newType = prompt('Тип:', n.type || 'Resale');
        const newEnds = prompt('Окончание аукциона:', n.auctionEnds || '');
        
        numbers[index] = {
            number: newNumber.trim(),
            minBid: newBid,
            status: newStatus === 'for_sale' ? 'for_sale' : 'on_auction',
            type: newType || 'Resale',
            auctionEnds: newEnds || ''
        };
        
        localStorage.setItem('jetstore_numbers', JSON.stringify(numbers));
        loadNumbersAdmin();
        showNotification('Номер изменён', 'success');
    } catch (error) {
        console.error('Ошибка редактирования номера:', error);
        showNotification('Ошибка при изменении', 'error');
    }
}

function deleteNumber(index) {
    if (!confirm('Удалить этот номер?')) return;
    
    try {
        const numbers = JSON.parse(localStorage.getItem('jetstore_numbers') || '[]');
        numbers.splice(index, 1);
        localStorage.setItem('jetstore_numbers', JSON.stringify(numbers));
        
        loadNumbersAdmin();
        showNotification('Номер удалён', 'success');
    } catch (error) {
        console.error('Ошибка удаления номера:', error);
        showNotification('Ошибка при удалении', 'error');
    }
}

// Загружаем при переходе в настройки
const originalLoadSettings = loadSettings;
loadSettings = function() {
    originalLoadSettings();
    loadUsernamesAdmin();
    loadNumbersAdmin();
};

// Экспортируем функции в глобальную область видимости
window.showAdminSection = showAdminSection;
window.showCategory = showCategory;
window.refreshStatistics = refreshStatistics;
window.editProduct = editProduct;
window.deleteProduct = deleteProduct;
window.saveProduct = saveProduct;
window.resetProductForm = resetProductForm;
window.editUser = editUser;
window.saveUser = saveUser;
window.resetUserForm = resetUserForm;
window.changePassword = changePassword;
window.saveCurrencyRates = saveCurrencyRates;
window.saveStarRate = saveStarRate;
window.saveStarsPrices = saveStarsPrices;
window.savePremiumPrices = savePremiumPrices;
window.switchSupercellCategory = switchSupercellCategory;
window.addSupercellProduct = addSupercellProduct;
window.editSupercellProduct = editSupercellProduct;
window.deleteSupercellProduct = deleteSupercellProduct;
window.exportData = exportData;
window.importData = importData;
window.resetData = resetData;
window.logout = logout;
window.addUsername = addUsername;
window.editUsername = editUsername;
window.deleteUsername = deleteUsername;
window.addNumber = addNumber;
window.editNumber = editNumber;
window.deleteNumber = deleteNumber;
window.loadUsernamesAdmin = loadUsernamesAdmin;
window.loadNumbersAdmin = loadNumbersAdmin;