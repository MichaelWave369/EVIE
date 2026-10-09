import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { syncMissionManifest } from './mission-audit.mjs';
import { resolve, dirname } from 'node:path';

const read = (path) => JSON.parse(readFileSync(resolve(import.meta.dirname, path), 'utf8'));
const save = (filename, data) => {
  const output = resolve(import.meta.dirname, '../src/generated/', filename);
  mkdirSync(dirname(output), { recursive: true });
  writeFileSync(output, JSON.stringify(data, null, 2) + '\n');
};
const architecture = read('../../app/shelf/architecture_cards.json');
if (architecture.schemaVersion !== 'evie.shelf.architecture-catalog/1' || architecture.cards.length !== 11) {
  throw Error('EVIE Architecture Pack catalog changed. Review before publishing.');
}
save('architecture.json', architecture);

const shelf = read('../../app/shelf/public_nested_catalog.json');
if (shelf.schemaVersion !== 'evie.shelf.public-nested/1' || shelf.source.totalCards !== 159 ||
    shelf.cards.length !== 159 || shelf.packs.length !== 9) {
  throw Error('Nested Shelf source missing or incomplete (expected 159 cards and 9 packs).');
}
const ids = new Set(), packIds = new Set();
for (const p of shelf.packs) {
  if (!p.id || packIds.has(p.id)) throw Error('Missing or duplicate pack ID: ' + p.id);
  packIds.add(p.id);
}
for (const c of shelf.cards) {
  if (!c.id || !c.slug || !c.name || ids.has(c.id) || !packIds.has(c.packId)) throw Error('Invalid nested shelf card: ' + c.id);
  if (!['catalog_only', 'bounded_adapter'].includes(c.status)) throw Error('Unreviewed execution status: ' + c.id);
  ids.add(c.id);
}
for (const p of shelf.packs) for (const id of p.includedIds) if (!ids.has(id)) {
  throw Error('Pack ' + p.id + ' references missing card ' + id);
}
const historicFloor = shelf.cards.find(c => c.id === 'shard_floor_plan_generator');
const checkedFloor = architecture.cards.find(c => c.card_id === 'shard_floor_plan_generator');
if (!historicFloor || !checkedFloor || historicFloor.status !== checkedFloor.execution.status) {
  throw Error('CAD producer status diverged from the audited Architecture Pack');
}
save('nested-shelf.json', shelf);
console.log('Synced:', shelf.cards.length, 'cards,', shelf.packs.length, 'packs; architecture audit:', architecture.cards.length, 'cards.');

const familySource = read('../../app/family_gate/family_targets.json');
if (familySource.schemaVersion !== 'evie.family-target-catalog/1' || !Array.isArray(familySource.targets)
    || familySource.targets.length !== 6 || familySource.transport !== 'not-implemented'
    || familySource.execution !== 'disabled') throw Error('Family Gate catalog drift / unsafe default');
const targetIds = new Set(familySource.targets.map(t => t.id));
if (targetIds.size !== familySource.targets.length) throw Error('Duplicate family target IDs');
save('family-targets.json', familySource);
syncMissionManifest();
