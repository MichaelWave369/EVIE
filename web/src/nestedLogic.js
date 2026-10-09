/** Pure read-only grouping and design-draft functions. Never executes cards. */
export const SHELF_SCHEMA = 'evie.shelf.public-nested/1';
export const DRAFT_SCHEMA = 'evie.deck.draft/1';
export const DECK_LIMIT = 32;

export function getPackCards(shelf, packId) {
  const pack = shelf.packs.find(p => p.id === packId);
  if (!pack) return [];
  if (pack.id === 'sovereign_all_access') return shelf.cards;
  const included = new Set(pack.includedIds ?? []);
  return shelf.cards.filter(c => c.packId === packId || included.has(c.id));
}

export function findLinkedCard(shelf, idOrSlug) {
  if (typeof idOrSlug !== 'string') return null;
  return shelf.cards.find(c => c.id === idOrSlug || c.slug === idOrSlug) ?? null;
}

export function filterCards(cards, { query = '', category = 'all', cardClass = 'all', stage = 'all' } = {}) {
  const q = query.trim().toLowerCase();
  return cards.filter(c =>
    (category === 'all' || c.category === category) &&
    (cardClass === 'all' || c.cardClass === cardClass) &&
    (stage === 'all' || c.stage === stage) &&
    (!q || [c.name, c.tagline, c.slug, c.category, c.id, ...c.inputs, ...c.outputs]
      .join(' ').toLowerCase().includes(q))
  );
}

export function reviewDraft(ids, cards, externalInputs = []) {
  const byId = new Map(cards.map(c => [c.id, c]));
  const available = new Set(externalInputs);
  const steps = [];
  for (const [index, id] of ids.entries()) {
    const card = byId.get(id);
    if (!card) {
      steps.push({ index, id, missing: ['unknown card'], status: 'catalog_only' });
      continue;
    }
    const missing = card.inputs.filter(input => !available.has(input));
    steps.push({ index, id, name: card.name, missing, status: card.status });
    for (const output of card.outputs) available.add(output);
  }
  return {
    steps,
    unresolved: steps.filter(s => s.missing.length).length,
    unverified: steps.filter(s => s.status !== 'bounded_adapter').length,
    executable: false,
    note: 'Design draft only. Contract matching is heuristic, not an executable workflow or certified validation.'
  };
}

export function makeDeckDraft(ids, shelf) {
  if (!Array.isArray(ids) || ids.length > DECK_LIMIT ||
      ids.some(id => typeof id !== 'string' || !shelf.cards.some(c => c.id === id))) {
    throw Error('Invalid deck selection');
  }
  const review = reviewDraft(ids, shelf.cards);
  return {
    schemaVersion: DRAFT_SCHEMA,
    origin: 'EVIE Commons public static Shelf',
    mode: 'design-only',
    createdAt: new Date().toISOString(),
    cards: ids.map((id, position) => ({ position, cardId: id })),
    validation: { unresolvedSteps: review.unresolved, unverifiedSteps: review.unverified, executable: false },
    note: review.note
  };
}
