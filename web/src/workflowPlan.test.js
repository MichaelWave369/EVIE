import { describe, expect, it } from 'vitest';
import manifest from './generated/mission-control.json';
import { availablePlanFlags, planEvieWorkflow } from './workflowPlan.js';

describe('R12 source-only EVIE workflow planner',()=>{
  it('plans real bounded CAD workflow without running CAD, DB or providers',()=>{
    const plan=planEvieWorkflow(manifest,'openblueprint_concept_floor_plan');
    expect(plan.schemaVersion).toBe('evie.workflow-preflight/1');
    expect(plan.summary.candidateModules).toBe(1);
    expect(plan.steps[0].name).toBe('openblueprint_floor_plan');
    expect(plan.databaseTouched).toBe(false);
    expect(plan.executionAuthorized).toBe(false);
    expect(plan.executed).toBe(false);
    expect(plan.sourceSha256).toBe(manifest.source.sha256);
  });
  it('skips optional audio/video unless explicitly opted into the flag',()=>{
    const base=planEvieWorkflow(manifest,'vault_to_lesson_pack');
    const audio=base.steps.find(s=>s.name==='audio_generator');
    expect(audio.condition).toBe('include_audio');
    expect(audio.decision).toBe('skipped_by_default');
    const plan=planEvieWorkflow(manifest,'vault_to_lesson_pack',['include_audio']);
    expect(plan.steps.find(s=>s.name==='audio_generator').decision).toBe('candidate_only');
    expect(plan.steps.find(s=>s.name==='video_generator').decision).toBe('skipped_by_default');
    expect(plan.executed).toBe(false);
  });
  it('expands nested publishing workflows and always flags effects for review',()=>{
    const flags=availablePlanFlags(manifest,'trend_to_money_publish');
    expect(flags).toContain('run_publish_workflow');
    const skip=planEvieWorkflow(manifest,'trend_to_money_publish');
    expect(skip.steps.find(s=>s.name==='vault_to_money_publish').decision).toBe('skipped_by_default');
    const include=planEvieWorkflow(manifest,'trend_to_money_publish',['run_publish_workflow']);
    expect(include.steps.some(s=>s.workflow==='vault_to_money_publish')).toBe(true);
    expect(include.steps.some(s=>s.name==='gumroad_publisher')).toBe(true);
    expect(include.summary.effectReviewCandidates).toBeGreaterThan(0);
    expect(include.steps.every(s=>s.executionAuthorized===false)).toBe(true);
  });
  it('rejects unknown flags and synthetic nested cycles before planning',()=>{
    expect(()=>planEvieWorkflow(manifest,'vault_to_lesson_pack',['publish_to_gumroad'])).toThrow('Unknown');
    expect(()=>planEvieWorkflow(manifest,'vault_to_lesson_pack',['include_audio','include_audio'])).toThrow('duplicate');
    const synthetic={
      ...manifest,
      workflows:[{id:'a',steps:[{index:1,module:null,workflow:'b',optional:false,whenConstraint:null}]},
        {id:'b',steps:[{index:1,module:null,workflow:'a',optional:false,whenConstraint:null}]}],
    };
    expect(()=>planEvieWorkflow(synthetic,'a')).toThrow('cycle');
  });
});
