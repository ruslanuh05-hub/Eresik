import express from 'express';
import helmet from 'helmet';
import fetch from 'node-fetch';
import https from 'https';
import path from 'path';
import { fileURLToPath } from 'url';
import { getSubscriptionByToken, isActive } from './lib/subscriptions.js';
import { startBot } from './bot.js';
import { openStore } from './lib/store.js';
import { listEffectivePlans, updatePlanPrice } from './lib/plans.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.disable('x-powered-by');
app.use(helmet({ contentSecurityPolicy: false }));
app.use(express.json());

// MVP: отдаём один готовый конфиг для USA.
// Позже заменим на выдачу персонального конфига (по токену из Telegram).
const CONFIG_PATH = process.env.JVPN_US_CONFIG_PATH || path.join(__dirname, 'configs', 'us.conf');

app.get('/health', (_req, res) => res.json({ ok: true }));

app.get('/configs/us', (_req, res) => {
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="jvpn-us.conf"');
  res.sendFile(CONFIG_PATH, (err) => {
    if (err) {
      res.status(500).send('Config not available');
    }
  });
});

// Subscriptions for v2raytun (token-gated, with expiry).
const DATA_DIR = process.env.JVPN_DATA_DIR || __dirname;
const store = openStore({ dataDir: DATA_DIR });

const UPSTREAM_SUB_URL = process.env.UPSTREAM_SUB_URL || null;
let upstreamCache = { atMs: 0, body: '' };
const UPSTREAM_CACHE_TTL_MS = Number(process.env.UPSTREAM_CACHE_TTL_MS || 30_000);
const UPSTREAM_TIMEOUT_MS = Number(process.env.UPSTREAM_TIMEOUT_MS || 8_000);
const UPSTREAM_INSECURE_TLS = String(process.env.UPSTREAM_INSECURE_TLS || '').toLowerCase() === '1' ||
  String(process.env.UPSTREAM_INSECURE_TLS || '').toLowerCase() === 'true';

async function getUpstreamSubscriptionText() {
  if (!UPSTREAM_SUB_URL) return '';
  const now = Date.now();
  if (upstreamCache.body && now - upstreamCache.atMs < UPSTREAM_CACHE_TTL_MS) return upstreamCache.body;

  const url = new URL(UPSTREAM_SUB_URL);
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  let resp;
  try {
    const agent =
      url.protocol === 'https:' && UPSTREAM_INSECURE_TLS
        ? new https.Agent({ rejectUnauthorized: false })
        : undefined;
    resp = await fetch(UPSTREAM_SUB_URL, {
      method: 'GET',
      headers: { 'user-agent': 'jvpn-backend/0.1' },
      signal: controller.signal,
      agent,
    });
  } finally {
    clearTimeout(t);
  }
  if (!resp.ok) throw new Error(`Upstream subscription fetch failed: ${resp.status}`);
  const body = await resp.text();
  upstreamCache = { atMs: now, body };
  return body;
}

app.get('/sub/:token.txt', async (req, res) => {
  const token = String(req.params.token || '').trim();
  if (!token || token.length < 10) {
    res.status(404).send('Not found');
    return;
  }

  const sub = getSubscriptionByToken(store, token);
  if (!isActive(sub)) {
    res.status(403).send('Subscription expired');
    return;
  }

  try {
    const upstream = await getUpstreamSubscriptionText();
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    res.send(
      [
        `# profile-title: JVPN`,
        `# token: ${sub.token}`,
        `# plan: ${sub.planId}`,
        `# expires-at-ms: ${sub.expiresAtMs}`,
        ``,
        upstream,
      ].join('\n')
    );
  } catch {
    res.status(502).send('Upstream not available');
  }
});

// Telegram bot (optional) — runs in the same process.
const BOT_TOKEN = process.env.TG_BOT_TOKEN || '';
const PROVIDER_TOKEN = process.env.TG_PROVIDER_TOKEN || '';
const BASE_URL = process.env.PUBLIC_BASE_URL || '';
const ADMIN_TG_IDS = (process.env.ADMIN_TG_IDS || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

// Simple Basic-auth admin API for managing plans.
const ADMIN_USER = process.env.ADMIN_USER || '';
const ADMIN_PASS = process.env.ADMIN_PASS || '';

function adminAuth(req, res, next) {
  if (!ADMIN_USER || !ADMIN_PASS) {
    res.status(403).send('Admin API disabled');
    return;
  }
  const header = req.headers.authorization || '';
  if (!header.startsWith('Basic ')) {
    res.setHeader('WWW-Authenticate', 'Basic realm="jvpn-admin"');
    res.status(401).send('Auth required');
    return;
  }
  let decoded = '';
  try {
    decoded = Buffer.from(header.slice(6), 'base64').toString('utf8');
  } catch {
    res.status(401).send('Bad auth header');
    return;
  }
  const colon = decoded.indexOf(':');
  const user = colon >= 0 ? decoded.slice(0, colon) : decoded;
  const pass = colon >= 0 ? decoded.slice(colon + 1) : '';
  if (user !== ADMIN_USER || pass !== ADMIN_PASS) {
    res.setHeader('WWW-Authenticate', 'Basic realm="jvpn-admin"');
    res.status(401).send('Invalid credentials');
    return;
  }
  next();
}

app.get('/admin/plans', adminAuth, (_req, res) => {
  res.json(listEffectivePlans(store));
});

app.post('/admin/plans/:id', adminAuth, (req, res) => {
  const id = String(req.params.id || '').trim();
  const { priceRub } = req.body || {};
  try {
    const updated = updatePlanPrice(store, id, priceRub);
    if (!updated) {
      res.status(404).send('Plan not found');
      return;
    }
    res.json(updated);
  } catch (err) {
    res.status(400).json({ error: err.message || 'Invalid data' });
  }
});

if (BOT_TOKEN && PROVIDER_TOKEN && BASE_URL) {
  startBot({
    store,
    botToken: BOT_TOKEN,
    providerToken: PROVIDER_TOKEN,
    baseUrl: BASE_URL,
    adminTgIds: ADMIN_TG_IDS,
  });
}

const port = Number(process.env.PORT || 8088);
app.listen(port, '0.0.0.0', () => {
  // eslint-disable-next-line no-console
  console.log(`JVPN backend listening on :${port}`);
});

