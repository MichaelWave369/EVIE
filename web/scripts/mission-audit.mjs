/** Public source-only capability manifest. No Python imports, agents, provider calls, or secrets. */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';

export const MISSION_SCHEMA = 'evie.mission-control.source/1';

export function parseModuleRegistry(source) {
  if (typeof source !== 'string') throw Error('Expected Python registry source');
  const start = source.indexOf('\nREGISTRY = {');
  if (start < 0) throw Error('EVIE REGISTRY marker missing');
  const end = source.indexOf('\n}', start);
  if (end < 0) throw Error('EVIE REGISTRY closing brace missing');
  const body = source.slice(start, end + 2);
  const matches = [...body.matchAll(/^\s*"([a-z0-9_]+)"\s*:\s*([A-Za-z_]\w*)\(\s*\),\s*$/gm)];
  if (!matches.length) throw Error('EVIE REGISTRY contains no recognized module entries');
  const modules = matches.map(match => ({ id: match[1], className: match[2] }));
  if (new Set(modules.map(m => m.id)).size !== modules.length) throw Error('Duplicate EVIE registry keys');
  const openingQuotes = [...body.matchAll(/^\s*"([a-z0-9_]+)"\s*:/gm)].length;
  if (openingQuotes !== matches.length) throw Error('Unsupported EVIE registry assignment: review parser');
  return modules;
}

export function moduleGroup(id) {
  if (/blueprint|cad|architect|structur|construction/.test(id)) return 'CAD & infrastructure';
  if (/publish|social|youtube|gumroad|payhip|distribution|launch/.test(id)) return 'Publishing & distribution';
  if (/image|visual|video|audio|cover|thumbnail|comfy|presentation|infographic|brandkit|podcast/.test(id)) return 'Media & design';
  if (/seo|funnel|sales|conversion|lead|pricing|storefront|offer/.test(id)) return 'Marketing & commerce';
  if (/vault|rag|index|research|trend|prediction|analytics|miner/.test(id)) return 'Knowledge & intelligence';
  return 'General & automation';
}

export function requiresEffectsReview(id) {
  return /publish|upload|gumroad|payhip|youtube_publisher|launch|scheduler|automation|execute|bridge|comfyui/.test(id);
}

export function inspectWorkflows(workflows, moduleNames) {
  if (!workflows || typeof workflows !== 'object' || Array.isArray(workflows)) throw Error('Workflow registry must be an object');
  const ids = new Set(Object.keys(workflows));
  const directUses = new Map([...moduleNames].map(id => [id, new Set()]));
  const graph = new Map();
  const result = [];
  for (const [id, value] of Object.entries(workflows)) {
    if (!value || !Array.isArray(value.steps)) throw Error('Malformed workflow: ' + id);
    const errors = [], references = [], nested = [], steps = [];
    for (const [index, step] of value.steps.entries()) {
      if (!step || typeof step !== 'object') { errors.push('invalid step ' + index); continue; }
      let module = step.module || null;
      let sub = step.workflow || null;
      if (typeof module === 'string' && module.startsWith('workflow:')) {
        sub = module.slice('workflow:'.length);
        module = null;
      }
      if (module && !moduleNames.has(module)) errors.push('unregistered module: ' + module);
      if (sub && !ids.has(sub)) errors.push('missing nested workflow: ' + sub);
      if (!module && !sub) errors.push('step has no module/workflow: ' + index);
      if (module) {
        references.push(module);
        directUses.get(module)?.add(id);
      }
      if (sub) nested.push(sub);
      steps.push({ index: index + 1, module, workflow: sub, optional: step.optional === true });
    }
    graph.set(id, nested);
    result.push({ id, description: String(value.description ?? '').slice(0, 240),
      tags: Array.isArray(value.tags) ? value.tags.filter(v => typeof v === 'string').slice(0, 12) : [],
      steps, modules: [...new Set(references)], nestedWorkflows: [...new Set(nested)],
      referenceIssues: errors, executionVerified: false });
  }
  const cycleNodes = new Set();
  const visit = (id, active, complete) => {
    if (active.has(id)) { cycleNodes.add(id); return true; }
    if (complete.has(id)) return false;
    active.add(id);
    let found = false;
    for (const next of graph.get(id) ?? []) if (ids.has(next) && visit(next, active, complete)) found = true;
    active.delete(id); complete.add(id);
    if (found) cycleNodes.add(id);
    return found;
  };
  const complete = new Set();
  for (const id of ids) visit(id, new Set(), complete);
  for (const wf of result) if (cycleNodes.has(wf.id)) wf.referenceIssues.push('nested workflow cycle detected');
  return { workflows: result, directUses, referenceIssues: result.flatMap(w => w.referenceIssues.map(message => ({ workflow: w.id, message }))) };
}

export function buildMissionManifest(registrySource, workflowSource) {
  const modules = parseModuleRegistry(registrySource);
  const workflows = JSON.parse(workflowSource);
  const examined = inspectWorkflows(workflows, new Set(modules.map(x => x.id)));
  const allModules = modules.map(mod => ({
    ...mod,
    group: moduleGroup(mod.id),
    workflowRefs: [...(examined.directUses.get(mod.id) ?? [])].sort(),
    effectfulReviewFlag: requiresEffectsReview(mod.id),
    evidence: mod.id === 'openblueprint_floor_plan'
      ? { level: 'targeted_test_source', path: 'tests/test_evie_local_revival.py',
          description: 'Disposable CAD producer smoke test exists in source. Not a local-machine runtime qualification.' }
      : { level: 'registration_only', description: 'Python registry entry, not proof of successful execution.' }
  }));
  const cadSourceSha256 = createHash('sha256').update(
    readFileSync(resolve(import.meta.dirname, '../../app/modules/openblueprint_floor_plan.py'))
  ).digest('hex');
  const qualificationFixtures = [{
    module: 'openblueprint_floor_plan',
    scenario: 'cad_rectangular_concept_v1',
    sourceSha256: cadSourceSha256,
    initialStatus: 'no_local_receipt',
    trust: 'local_unsigned_unverified',
  }];
  const inWorkflows = allModules.filter(m => m.workflowRefs.length).length;
  const digest = createHash('sha256').update(registrySource).update('\n--- workflow ---\n').update(workflowSource).digest('hex');
  return {
    schemaVersion: MISSION_SCHEMA,
    source: { kind: 'build_time_source_snapshot', revision: 'checked-in GitHub source',
      sha256: digest, publicOnly: true,
      files: ['app/modules/__init__.py', 'configs/workflows.json'],
      noLiveBackend: true },
    summary: { registeredModules: allModules.length, configuredWorkflows: examined.workflows.length,
      directlyUsedModules: inWorkflows, referenceIssues: examined.referenceIssues.length,
      sourceTestWiredModules: allModules.filter(m => m.evidence.level === 'targeted_test_source').length,
      runtimeQualifiedModules: 0 },
    qualificationFixtures,
    modules: allModules, workflows: examined.workflows,
    referenceIssues: examined.referenceIssues,
    limitations: [
      'Registration does not prove module execution. Historical Shelf cards are separate.',
      'Only explicit test-source evidence is indexed. Zero live module qualifications are claimed.',
      'Potential external-effect flags are conservative naming heuristics, not security audits.',
      'The public static React site does not connect to the private EVIE API or invoke workflows.'
    ]
  };
}

export function syncMissionManifest() {
  const source = readFileSync(resolve(import.meta.dirname, '../../app/modules/__init__.py'), 'utf8');
  const flows = readFileSync(resolve(import.meta.dirname, '../../configs/workflows.json'), 'utf8');
  const snapshot = buildMissionManifest(source, flows);
  if (snapshot.summary.referenceIssues) throw Error('EVIE workflow references are broken. Review before publishing.');
  const output = resolve(import.meta.dirname, '../src/generated/mission-control.json');
  mkdirSync(dirname(output), { recursive: true });
  writeFileSync(output, JSON.stringify(snapshot, null, 2) + '\n');
  console.log('Mission Control:', snapshot.summary.registeredModules, 'modules,',
    snapshot.summary.configuredWorkflows, 'workflows,', snapshot.summary.directlyUsedModules, 'directly used modules.');
  return snapshot;
}
