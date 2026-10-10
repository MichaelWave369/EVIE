/** R12 EVIE workflow source-only preflight. No network, DB, providers or dispatch. */
export const PLAN_SCHEMA = 'evie.workflow-preflight/1';
export const MAX_PLAN_ROWS = 128;
export const MAX_DEPTH = 12;
const RISK = /publish|upload|gumroad|payhip|launch|scheduler|automation|execute|bridge|comfyui/;

function getWorkflow(manifest, name) {
  const workflow = manifest?.workflows?.find(w=>w.id===name);
  if(!workflow)throw Error('Unknown EVIE workflow.');
  return workflow;
}

export function availablePlanFlags(manifest, id) {
  const flags=new Set();
  const visited=new Set();
  function walk(name, stack){
    if(stack.includes(name))throw Error('Nested workflow cycle detected.');
    if(visited.has(name))return;
    visited.add(name);
    for(const step of getWorkflow(manifest,name).steps){
      if(step.whenConstraint){
        if(!/^[a-z][a-z0-9_]{0,63}$/.test(step.whenConstraint))throw Error('Invalid workflow condition.');
        flags.add(step.whenConstraint);
      }
      if(step.workflow)walk(step.workflow,[...stack,name]);
    }
  }
  walk(id,[]);
  return [...flags].sort();
}

export function planEvieWorkflow(manifest,id,selectedFlags=[]) {
  const source=manifest?.source?.sha256;
  if(typeof source!=='string'||!/^[a-f0-9]{64}$/.test(source))throw Error('Missing source provenance.');
  if(!Array.isArray(selectedFlags)||selectedFlags.some(x=>typeof x!=='string'))throw Error('Invalid flag input.');
  const available=availablePlanFlags(manifest,id);
  const allowed=new Set(available);
  const choices=new Set(selectedFlags);
  if(choices.size!==selectedFlags.length||selectedFlags.some(x=>!allowed.has(x)))
    throw Error('Unknown or duplicate workflow flag.');
  const steps=[],problems=[];
  function walk(current,lineage) {
    if(lineage.includes(current)||lineage.length>=MAX_DEPTH)throw Error('Nested workflow cycle or depth limit.');
    const workflow=getWorkflow(manifest,current);
    for(const step of workflow.steps) {
      if(steps.length>=MAX_PLAN_ROWS)throw Error('Workflow plan exceeds bounded step limit.');
      if(Boolean(step.module)===Boolean(step.workflow))throw Error('Ambiguous workflow step.');
      const enabled=!step.whenConstraint||choices.has(step.whenConstraint);
      const risky=Boolean(step.module&&RISK.test(step.module));
      if(step.module&&!manifest.modules.some(m=>m.id===step.module))problems.push('unregistered module');
      const row={
        path:[...lineage,current,String(step.index)].join('/'),
        workflow:current,index:step.index,
        kind:step.workflow?'nested':'module',name:step.workflow||step.module,
        optional:step.optional===true, condition:step.whenConstraint||null,
        decision:enabled?'candidate_only':'skipped_by_default',
        effectReview:risky,executionAuthorized:false,executed:false,
      };
      steps.push(row);
      if(enabled&&step.workflow)walk(step.workflow,[...lineage,current]);
    }
  }
  walk(id,[]);
  return {
    schemaVersion:PLAN_SCHEMA,workflow:id,sourceSha256:source,
    enabledFlags:[...choices].sort(),availableFlags:available,steps,
    summary:{
      planRows:steps.length,
      candidateModules:steps.filter(x=>x.kind==='module'&&x.decision==='candidate_only').length,
      effectReviewCandidates:steps.filter(x=>x.effectReview&&x.decision==='candidate_only').length,
      skippedRows:steps.filter(x=>x.decision==='skipped_by_default').length,
      registryProblems:problems,
    },
    evidence:'source-plan-only',databaseTouched:false,executionAuthorized:false,
    executed:false,providerAvailabilityVerified:false,
    note:'Read-only plan from checked-in source. No modules, providers, DB or nested runners invoked.',
  };
}
