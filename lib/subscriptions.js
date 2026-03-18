import crypto from 'crypto';

function nowMs() {
  return Date.now();
}

export function createToken() {
  // URL-safe, short-ish.
  return crypto.randomBytes(24).toString('base64url');
}

export function createSubscription(store, { tgUserId, planId, durationDays }) {
  const token = createToken();
  const createdAt = nowMs();
  const expiresAt = createdAt + durationDays * 24 * 60 * 60 * 1000;

  const record = {
    token,
    tgUserId: String(tgUserId),
    planId,
    createdAtMs: createdAt,
    expiresAtMs: expiresAt,
  };

  store.upsert(record);

  return { token, createdAt, expiresAt };
}

export function getSubscriptionByToken(store, token) {
  return store.getByToken(token) || null;
}

export function isActive(sub) {
  return Boolean(sub && Number(sub.expiresAtMs) > nowMs());
}

