import fs from 'fs';
import path from 'path';

function safeParseJson(text, fallback) {
  try {
    return JSON.parse(text);
  } catch {
    return fallback;
  }
}

function atomicWriteFileSync(filePath, data) {
  const tmp = `${filePath}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, data, 'utf8');
  fs.renameSync(tmp, filePath);
}

export function openStore({ dataDir }) {
  const filePath = path.join(dataDir, 'subscriptions.json');

  /** @type {Map<string, any>} */
  const byToken = new Map();
  /** @type {Map<string, any>} */
  const users = new Map();
  /** @type {Map<string, any>} */
  const plans = new Map();

  if (fs.existsSync(filePath)) {
    const raw = fs.readFileSync(filePath, 'utf8');
    const parsed = safeParseJson(raw, { subscriptions: [], users: {}, plans: {} });
    for (const sub of parsed.subscriptions || []) {
      if (sub?.token) byToken.set(String(sub.token), sub);
    }
    const parsedUsers = parsed.users || {};
    for (const [tgUserId, user] of Object.entries(parsedUsers)) {
      if (!tgUserId) continue;
      users.set(String(tgUserId), user || {});
    }
    const parsedPlans = parsed.plans || {};
    for (const [id, plan] of Object.entries(parsedPlans)) {
      if (!id) continue;
      plans.set(String(id), plan || {});
    }
  }

  let dirty = false;
  const flush = () => {
    if (!dirty) return;
    const body = JSON.stringify(
      {
        subscriptions: Array.from(byToken.values()),
        users: Object.fromEntries(users.entries()),
        plans: Object.fromEntries(plans.entries()),
      },
      null,
      2
    );
    atomicWriteFileSync(filePath, body);
    dirty = false;
  };

  const scheduleFlush = () => {
    dirty = true;
    // Debounce a bit; good enough for MVP.
    setTimeout(flush, 250).unref?.();
  };

  process.on('exit', flush);
  process.on('SIGINT', () => {
    flush();
    process.exit(0);
  });
  process.on('SIGTERM', () => {
    flush();
    process.exit(0);
  });

  return {
    filePath,
    getByToken(token) {
      return byToken.get(String(token));
    },
    upsert(sub) {
      byToken.set(String(sub.token), sub);
      scheduleFlush();
    },
    getUser(tgUserId) {
      return users.get(String(tgUserId)) || null;
    },
    upsertUser(tgUserId, patch) {
      const id = String(tgUserId);
      const prev = users.get(id) || {};
      users.set(id, { ...prev, ...patch });
      scheduleFlush();
    },
    getPlans() {
      return Object.fromEntries(plans.entries());
    },
    upsertPlan(id, patch) {
      const key = String(id);
      const prev = plans.get(key) || {};
      plans.set(key, { ...prev, ...patch, id: key });
      scheduleFlush();
    },
  };
}

