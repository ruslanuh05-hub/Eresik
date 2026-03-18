import { Telegraf, Markup } from 'telegraf';
import { createSubscription } from './lib/subscriptions.js';
import { listEffectivePlans, getEffectivePlanById } from './lib/plans.js';

const CAPTCHA_EMOJIS = ['🐶', '🐱', '🦊', '🐼', '🐸', '🐵', '🦄', '🐯', '🐨', '🦁', '🐙', '🐧', '🦉'];
const CAPTCHA_CHOICES = 4;
const CAPTCHA_TTL_MS = 5 * 60 * 1000;

function rubToTelegramAmount(rub) {
  // Telegram expects amounts in the smallest units (kopeks).
  return Math.round(Number(rub) * 100);
}

export function startBot({ store, botToken, providerToken, baseUrl, adminTgIds = [] }) {
  const bot = new Telegraf(botToken);

  /** @type {Map<string, {correct: string, expiresAtMs: number}>} */
  const pendingCaptchaByUser = new Map();

  function pickRandom(arr, n) {
    const copy = [...arr];
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy.slice(0, n);
  }

  function plansKeyboard() {
    const plans = listEffectivePlans(store);
    return Markup.inlineKeyboard(
      plans.map((p) => [Markup.button.callback(`${p.title} — ${p.priceRub}₽`, `buy:${p.id}`)])
    );
  }

  async function sendCaptcha(ctx) {
    const correct = CAPTCHA_EMOJIS[Math.floor(Math.random() * CAPTCHA_EMOJIS.length)];
    const choices = pickRandom(
      Array.from(new Set([correct, ...pickRandom(CAPTCHA_EMOJIS, CAPTCHA_CHOICES * 2)])),
      CAPTCHA_CHOICES
    );
    if (!choices.includes(correct)) choices[0] = correct;

    pendingCaptchaByUser.set(String(ctx.from.id), { correct, expiresAtMs: Date.now() + CAPTCHA_TTL_MS });

    const kb = Markup.inlineKeyboard(choices.map((e) => Markup.button.callback(e, `verify:${e}`)));
    await ctx.reply(`Проверка: нажмите эмодзи ${correct}`, kb);
  }

  async function afterVerified(ctx) {
    const kb = plansKeyboard();
    await ctx.reply(
      'Готово.\n\nВыберите тариф — после оплаты пришлю персональную ссылку подписки для v2raytun.',
      kb
    );
  }

  bot.start(async (ctx) => {
    const user = store.getUser(ctx.from.id) || {};
    if (user.verifiedAtMs) {
      await afterVerified(ctx);
      return;
    }
    await ctx.reply('Перед покупкой нужно пройти быструю проверку, что вы не бот.');
    await sendCaptcha(ctx);
  });

  bot.command('plans', async (ctx) => {
    const plans = listEffectivePlans(store);
    const text = plans.map((p) => `- ${p.title}: ${p.priceRub}₽`).join('\n');
    await ctx.reply(`Тарифы:\n${text}\n\nНажмите /start чтобы купить.`);
  });

  bot.command('my', async (ctx) => {
    await ctx.reply('После оплаты я пришлю вашу ссылку подписки. Если потеряли — напишите /start и купите заново или обратитесь к администратору.');
  });

  bot.action(/^verify:(.+)$/i, async (ctx) => {
    const chosen = ctx.match?.[1];
    const userId = String(ctx.from.id);
    const pending = pendingCaptchaByUser.get(userId);
    if (!pending || pending.expiresAtMs < Date.now()) {
      pendingCaptchaByUser.delete(userId);
      await ctx.answerCbQuery('Проверка устарела, попробуйте ещё раз');
      await sendCaptcha(ctx);
      return;
    }
    if (chosen !== pending.correct) {
      await ctx.answerCbQuery('Неверно. Попробуйте ещё раз');
      await sendCaptcha(ctx);
      return;
    }

    pendingCaptchaByUser.delete(userId);
    store.upsertUser(userId, { verifiedAtMs: Date.now() });
    await ctx.answerCbQuery('Проверка пройдена');

    const user = store.getUser(userId) || {};
    if (!user.trialUsedAtMs) {
      const { token, expiresAt } = createSubscription(store, {
        tgUserId: userId,
        planId: 'trial-1d',
        durationDays: 1,
      });
      store.upsertUser(userId, { trialUsedAtMs: Date.now() });

      const url = `${baseUrl.replace(/\/+$/, '')}/sub/${token}.txt`;
      const expires = new Date(expiresAt).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
      await ctx.reply(
        `Пробный период активирован на 1 день.\n\nВаша ссылка подписки (добавьте в v2raytun как Subscription URL):\n${url}\n\nДействует до: ${expires}`
      );
    }

    await afterVerified(ctx);
  });

  bot.action(/^buy:(.+)$/i, async (ctx) => {
    const planId = ctx.match?.[1];
    const plan = getEffectivePlanById(store, planId);
    if (!plan) {
      await ctx.answerCbQuery('Неизвестный тариф');
      return;
    }

    const user = store.getUser(ctx.from.id) || {};
    if (!user.verifiedAtMs) {
      await ctx.answerCbQuery('Сначала пройдите проверку');
      await sendCaptcha(ctx);
      return;
    }

    await ctx.answerCbQuery();

    const payload = JSON.stringify({
      v: 1,
      planId: plan.id,
      tgUserId: String(ctx.from.id),
      ts: Date.now(),
      nonce: Math.random().toString(36).slice(2),
    });

    if (!providerToken) {
      await ctx.reply('Оплата через Telegram сейчас отключена. Используйте оплату по ссылке (FreeKassa) или напишите администратору.');
      return;
    }

    await ctx.replyWithInvoice({
      title: `VPN — ${plan.title}`,
      description: 'Доступ к персональной подписке для v2raytun.',
      payload,
      provider_token: providerToken,
      currency: 'RUB',
      prices: [{ label: plan.title, amount: rubToTelegramAmount(plan.priceRub) }],
      start_parameter: `jvpn_${plan.id}`,
    });
  });

  bot.on('pre_checkout_query', async (ctx) => {
    // Approve all checkout queries; validate payload structure minimally.
    try {
      JSON.parse(ctx.preCheckoutQuery.invoice_payload);
      await ctx.answerPreCheckoutQuery(true);
    } catch {
      await ctx.answerPreCheckoutQuery(false, 'Некорректный платёж');
    }
  });

  bot.on('successful_payment', async (ctx) => {
    const payloadRaw = ctx.message.successful_payment.invoice_payload;
    let payload;
    try {
      payload = JSON.parse(payloadRaw);
    } catch {
      payload = null;
    }

    const plan = getEffectivePlanById(store, payload?.planId);
    if (!plan) {
      await ctx.reply('Платёж прошёл, но тариф не распознан. Напишите администратору.');
      return;
    }

    const { token, expiresAt } = createSubscription(store, {
      tgUserId: ctx.from.id,
      planId: plan.id,
      durationDays: plan.days,
    });

    const url = `${baseUrl.replace(/\/+$/, '')}/sub/${token}.txt`;
    const expires = new Date(expiresAt).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

    await ctx.reply(
      `Оплата получена.\n\nВаша ссылка подписки (добавьте в v2raytun как Subscription URL):\n${url}\n\nДействует до: ${expires}`
    );

    for (const adminId of adminTgIds) {
      try {
        await ctx.telegram.sendMessage(
          adminId,
          `Новая оплата: ${plan.title} (${plan.priceRub}₽)\nuser=${ctx.from.id} @${ctx.from.username || '-'}\nsub=${url}`
        );
      } catch {
        // ignore
      }
    }
  });

  bot.catch((_err, _ctx) => {
    // Avoid crashing the whole process on bot errors.
  });

  bot.launch();
  return bot;
}

