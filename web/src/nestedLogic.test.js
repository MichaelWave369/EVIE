import { describe, expect, it } from 'vitest';
import shelf from './generated/nested-shelf.json';
import { DECK_LIMIT, getPackCards, findLinkedCard, filterCards, reviewDraft, makeDeckDraft } from './nestedLogic.js';

describe('recovered nested Sovereign Shelf', () => {
  it('contains 159 unique cards, nine packs, seven classes, with truthful status', () => {
    expect(shelf.cards).toHaveLength(159);
    expect(shelf.packs).toHaveLength(9);
    expect(new Set(shelf.cards.map(c => c.id)).size).toBe(159);
    expect(new Set(shelf.cards.map(c => c.cardClass)).size).toBe(7);
    expect(shelf.cards.filter(c => c.status === 'bounded_adapter').map(c => c.id))
      .toEqual(['shard_floor_plan_generator']);
  });
  it('nests cards by pack, including the all-access root, without losing archive cards', () => {
    expect(getPackCards(shelf, 'sovereign_all_access')).toHaveLength(159);
    expect(getPackCards(shelf, 'architecture_pack').length).toBeGreaterThanOrEqual(11);
    expect(getPackCards(shelf, 'not-a-pack')).toHaveLength(0);
    expect(findLinkedCard(shelf, 'shard_concept_parser').slug).toBe('concept_parser');
    expect(findLinkedCard(shelf, 'floor_plan_generator').id).toBe('shard_floor_plan_generator');
  });
  it('searches by input/output and filters by category/class/stage', () => {
    const matching = filterCards(shelf.cards, { query: 'floor_plan_dxf' });
    expect(matching.some(c => c.id === 'shard_floor_plan_generator')).toBe(true);
    expect(filterCards(shelf.cards, { category: 'architecture', cardClass: 'shard' }).length).toBe(11);
    expect(filterCards(shelf.cards, { stage: 'NO SUCH STAGE' })).toHaveLength(0);
  });
  it('displays unverified dependency and execution flags without executing anything', () => {
    const two = ['shard_concept_parser', 'shard_floor_plan_generator'];
    const result = reviewDraft(two, shelf.cards);
    expect(result.executable).toBe(false);
    expect(result.steps[0].missing).toContain('structure_description');
    expect(result.steps[1].missing).not.toContain('structure_spec');
    expect(result.unverified).toBeGreaterThan(0);
  });
  it('exports design-only metadata and refuses invalid/oversized decks', () => {
    const draft = makeDeckDraft(['shard_floor_plan_generator'], shelf);
    expect(draft.schemaVersion).toBe('evie.deck.draft/1');
    expect(draft.mode).toBe('design-only');
    expect(draft.validation.executable).toBe(false);
    expect(() => makeDeckDraft(['not-a-card'], shelf)).toThrow('Invalid');
    expect(() => makeDeckDraft(Array(DECK_LIMIT + 1).fill('shard_floor_plan_generator'), shelf)).toThrow('Invalid');
  });
});
