import { describe, expect, it } from 'vitest';
import targets from './generated/family-targets.json';
import { MAX_ARTIFACT_BYTES, createFamilyProposal } from './familyGateLogic.js';

const base = {
  target: 'openblue', artifactKind: 'openblueprint.evie-proposal/1',
  sha256: 'a'.repeat(64), size: 120,
  createdAt: '2026-10-09T19:00:00.000Z',
  nonce: '1'.repeat(32),
};
describe('R8B public Family Gate keeps all effects disabled', () => {
  it('contains six intended destinations but does not expose any transport/executor', () => {
    expect(targets.schemaVersion).toBe('evie.family-target-catalog/1');
    expect(targets.targets).toHaveLength(6);
    expect(targets.transport).toBe('not-implemented');
    expect(targets.execution).toBe('disabled');
  });
  it('builds a bounded local-only artifact review request', () => {
    const result = createFamilyProposal(base, targets);
    expect(result.schemaVersion).toBe('evie.family-handoff-proposal/1');
    expect(result.executionAuthorized).toBe(false);
    expect(result.transportEnabled).toBe(false);
    expect(result.requestedEffects).toEqual([]);
    expect(result.intent).toBe('manual_inspection_only');
    expect(Date.parse(result.expiresAt) - Date.parse(result.createdAt)).toBe(900_000);
  });
  it('rejects unauthorized targets, wrong artifact kinds, oversize files, lifetime bypass', () => {
    for (const change of [
      { target:'gmail' }, { artifactKind:'application/x-executable' },
      { size:0 }, { size:MAX_ARTIFACT_BYTES+1 }, { sha256:'bad' },
      { nonce:'../file' }, { ttlMinutes:120 }, { createdAt:'not-a-date' },
    ]) expect(() => createFamilyProposal({...base, ...change}, targets)).toThrow();
  });
});
