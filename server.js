// Простое Node/Express API для поиска Telegram-пользователя по username
// Эндпоинт: GET /api/telegram/user?username=<username>
//
// Требуется переменная окружения BOT_TOKEN с токеном вашего бота.

import express from 'express';
import fetch from 'node-fetch';

const app = express();
const port = process.env.PORT || 3000;
const botToken = process.env.BOT_TOKEN;

if (!botToken) {
  console.warn(
    '[WARN] Переменная окружения BOT_TOKEN не задана. ' +
      'Эндпоинт /api/telegram/user работать не будет, пока вы её не установите.'
  );
}

app.use(express.json());

// Хелпер для запросов к Bot API
async function callTelegram(method, params) {
  const url = new URL(`https://api.telegram.org/bot${botToken}/${method}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Telegram API HTTP error: ${res.status}`);
  }
  const data = await res.json();
  if (!data.ok) {
    const err = new Error(data.description || 'Telegram API error');
    err.code = data.error_code;
    throw err;
  }
  return data.result;
}

// Получение URL аватарки по file_id
async function getFileUrl(fileId) {
  if (!fileId) return null;
  const result = await callTelegram('getFile', { file_id: fileId });
  if (!result || !result.file_path) return null;
  return `https://api.telegram.org/file/bot${botToken}/${result.file_path}`;
}

// Основной эндпоинт поиска пользователя
app.get('/api/telegram/user', async (req, res) => {
  try {
    if (!botToken) {
      return res
        .status(500)
        .json({ error: 'bot_token_missing', message: 'BOT_TOKEN не сконфигурирован на сервере' });
    }

    const rawUsername = (req.query.username || '').toString().trim();
    if (!rawUsername) {
      return res.status(400).json({ error: 'bad_request', message: 'username is required' });
    }

    const cleanUsername = rawUsername.replace(/^@/, '');

    // 1. Получаем информацию о чате пользователя
    // getChat позволяет искать по @username
    let chat;
    try {
      chat = await callTelegram('getChat', { username: cleanUsername });
    } catch (err) {
      // Если Telegram вернул ошибку 400/404 — считаем, что пользователь не найден
      return res.status(404).json({ error: 'not_found', message: 'User not found' });
    }

    // 2. Пытаемся получить аватарку
    let avatarUrl = null;

    // В некоторых версиях getChat возвращает поле photo с small_file_id / big_file_id
    if (chat.photo && (chat.photo.small_file_id || chat.photo.big_file_id)) {
      avatarUrl = await getFileUrl(chat.photo.big_file_id || chat.photo.small_file_id);
    } else {
      // Если photo нет — можно попробовать getUserProfilePhotos по user_id
      // (для обычных пользователей chat.id == user_id)
      try {
        const photos = await callTelegram('getUserProfilePhotos', {
          user_id: chat.id,
          limit: 1
        });
        if (photos.total_count > 0 && photos.photos[0][0]?.file_id) {
          avatarUrl = await getFileUrl(photos.photos[0][0].file_id);
        }
      } catch {
        // Если тут ошибка — просто оставляем avatarUrl = null
      }
    }

    const payload = {
      username: chat.username || cleanUsername,
      firstName: chat.first_name || '',
      lastName: chat.last_name || '',
      avatar: avatarUrl
    };

    return res.json(payload);
  } catch (err) {
    console.error('Ошибка в /api/telegram/user:', err);
    return res.status(500).json({ error: 'internal_error', message: 'Internal server error' });
  }
});

app.listen(port, () => {
  console.log(`JET mini-app backend запущен на порту ${port}`);
});

