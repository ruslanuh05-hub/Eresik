const DEFAULT_PLANS = [
  { id: 'd7', title: '7 дней', days: 7, defaultPriceRub: 99 },
  { id: 'd30', title: '30 дней', days: 30, defaultPriceRub: 199 },
  { id: 'd60', title: '60 дней', days: 60, defaultPriceRub: 349 },
  { id: 'd90', title: '90 дней', days: 90, defaultPriceRub: 499 },
];

export function listEffectivePlans(store) {
  const stored = store.getPlans ? store.getPlans() : {};
  return DEFAULT_PLANS.map((base) => {
    const saved = stored[base.id] || {};
    const priceRub =
      typeof saved.priceRub === 'number' && Number.isFinite(saved.priceRub) && saved.priceRub > 0
        ? saved.priceRub
        : base.defaultPriceRub;
    const days = typeof saved.days === 'number' && saved.days > 0 ? saved.days : base.days;
    const title = saved.title || base.title;
    return { id: base.id, title, days, priceRub };
  });
}

export function getEffectivePlanById(store, id) {
  return listEffectivePlans(store).find((p) => p.id === id) || null;
}

export function updatePlanPrice(store, id, priceRub) {
  const plan = getEffectivePlanById(store, id);
  if (!plan) return null;
  const cleanPrice = Number(priceRub);
  if (!Number.isFinite(cleanPrice) || cleanPrice <= 0) {
    throw new Error('Invalid price');
  }
  if (store.upsertPlan) {
    store.upsertPlan(id, { priceRub: cleanPrice, days: plan.days, title: plan.title });
  }
  return { ...plan, priceRub: cleanPrice };
}

export { DEFAULT_PLANS };

