import { describe, expect, it } from 'vitest';
import catalog from './generated/mission-control.json';
import { examineLocalReceipt } from './receiptReview.js';

function example() {
  return {
    schemaVersion: 'evie.qualification-receipt/1',
    module: 'openblueprint_floor_plan',
    scenario: 'cad_rectangular_concept_v1',
    status: 'pass',
    origin: 'local-subprocess-observation',
    createdAt: '2026-10-09T17:00:00Z',
    durationMs: 178,
    sourceSha256: catalog.qualificationFixtures[0].sourceSha256,
    artifactSha256: 'a'.repeat(64),
    checks: Object.fromEntries([
      'versioned_proposal','versioned_project','bounded_wall_geometry','symbol_types',
      'unique_element_ids','source_labels','run_id_bound','digest_match','artifact_scope',
    ].map(key => [key, true])),
    trust: { signed: false, authenticatedMachine: false },
    effectPolicy: { temporaryWorkspace: true, providerEnvironmentStripped: true,
      networkSandboxEnforced: false, externalEffectsAuthorized: false },
  };
}
const parse = value => examineLocalReceipt(JSON.stringify(value), catalog);
describe('R7 local-only qualification receipt inspector', () => {
  it('inspects an allowlisted example while clearly refusing authentication', () => {
    const result = parse(example());
    expect(result.status).toBe('pass');
    expect(result.checkCount).toBe(9);
    expect(result.sourceMatch).toBe(true);
    expect(result.authenticated).toBe(false);
    expect(result.level).toBe('unsigned_local_self_report');
    expect(catalog.summary.runtimeQualifiedModules).toBe(0);
  });
  it('rejects unknown modules, forged source revisions and claiming signatures', () => {
    expect(() => parse({ ...example(), module: 'youtube_publisher' })).toThrow('not in');
    expect(() => parse({ ...example(), sourceSha256: 'b'.repeat(64) })).toThrow('does not match');
    expect(() => parse({ ...example(), trust: {signed: true, authenticatedMachine:true} })).toThrow('policy');
  });
  it('rejects false PASS, missing checks and invalid JSON', () => {
    expect(() => parse({ ...example(), checks: {versioned_proposal: true} })).toThrow('required checks');
    expect(() => parse({ ...example(), artifactSha256: 'bad' })).toThrow('artifact digest');
    expect(() => examineLocalReceipt('<garbage>', catalog)).toThrow('Invalid receipt');
    expect(() => examineLocalReceipt('a'.repeat(64001), catalog)).toThrow('too large');
  });
});
