import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { buildMissionManifest, inspectWorkflows, parseModuleRegistry } from '../scripts/mission-audit.mjs';
import snapshot from './generated/mission-control.json';

describe('Mission Control source provenance and accuracy', () => {
  it('derives all module keys strictly from Python registry entries', () => {
    expect(parseModuleRegistry('\nREGISTRY = {\n    "one": OneModule(),\n    "two": TwoModule(),\n}\n'))
      .toEqual([{ id: 'one', className: 'OneModule' }, { id: 'two', className: 'TwoModule' }]);
    expect(() => parseModuleRegistry('\nREGISTRY = {\n    "one": OneModule(),\n    "one": TwoModule(),\n}\n'))
      .toThrow('Duplicate');
  });
  it('identifies broken dependencies and nested cycles without running workflows', () => {
    const examined = inspectWorkflows({
      a: { steps: [{ module: 'known' }, { workflow: 'b' }] },
      b: { steps: [{ workflow: 'a' }, { module: 'missing' }] }
    }, new Set(['known']));
    expect(examined.referenceIssues.some(x => x.message.includes('unregistered'))).toBe(true);
    expect(examined.referenceIssues.some(x => x.message.includes('cycle'))).toBe(true);
    expect(examined.directUses.get('known').has('a')).toBe(true);
  });
  it('matches committed source and never claims live runtime qualification', () => {
    const py = readFileSync(resolve(import.meta.dirname, '../../app/modules/__init__.py'), 'utf8');
    const json = readFileSync(resolve(import.meta.dirname, '../../configs/workflows.json'), 'utf8');
    const report = buildMissionManifest(py, json);
    expect(report.summary.registeredModules).toBe(117);
    expect(report.summary.configuredWorkflows).toBe(12);
    expect(report.summary.referenceIssues).toBe(0);
    expect(report.summary.runtimeQualifiedModules).toBe(0);
    expect(snapshot.source.sha256).toBe(report.source.sha256);
    expect(snapshot.modules.map(x => x.id)).toEqual(report.modules.map(x => x.id));
    expect(snapshot.modules.every(m => ['registration_only','targeted_test_source'].includes(m.evidence.level))).toBe(true);
  });
  it('does not include vaults, API key values, or execution controls', () => {
    const text = JSON.stringify(snapshot);
    expect(snapshot.source.noLiveBackend).toBe(true);
    expect(text).not.toMatch(/EV_API_KEY=|api_key_value|bearer_token|execution_token/);
    expect(snapshot.modules.filter(m => m.evidence.level === 'targeted_test_source').map(m => m.id))
      .toEqual(['openblueprint_floor_plan']);
  });
});
