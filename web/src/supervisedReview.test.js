import { describe, expect, it } from 'vitest';
import { webcrypto } from 'node:crypto';
import manifest from './generated/mission-control.json';
import { createDemoProposal } from './blueprint.js';
import { inspectSupervisedReview } from './supervisedReview.js';

async function fixture() {
  const proposal=createDemoProposal({width:24,depth:16,partition:'vertical',title:'EVIE Supervised Concept'});
  proposal.source={system:'EVIE',cardId:'openblueprint_floor_plan',runId:'evie-cad-testfixture',mode:'generated'};
  proposal.project.walls.forEach((w,i)=>w.id=['evie-n','evie-e','evie-s','evie-w','evie-p'][i]);
  proposal.project.symbols[0].id='evie-door';
  proposal.project.symbols[1].id='evie-net';
  const bytes=new TextEncoder().encode(JSON.stringify(proposal));
  const sha=Buffer.from(await webcrypto.subtle.digest('SHA-256',bytes)).toString('hex');
  const receipt={
    schemaVersion:'evie.supervised-cad-review/1',status:'staged_for_human_review',
    workflow:'openblueprint_concept_floor_plan',module:'openblueprint_floor_plan',
    scenario:'cad_supervised_24x16_v1',origin:'local-unsigned-observation',
    producerRunId:'evie-cad-testfixture',artifactSha256:sha,artifactBytes:bytes.length,
    workflowSourceSha256:manifest.source.sha256,
    producerSourceSha256:manifest.qualificationFixtures[0].sourceSha256,
    walls:5,symbols:2,units:'ft',
    evidence:{fixedWorkflowStepsMatched:true,proposalSchemaValidated:true,
      outputDigestVerified:true,geometryVerified:true},
    governance:{localFixtureExecuted:true,legacyRunnerInvoked:false,
      databaseTouched:false,providerCredentialsProvided:false,networkSandboxEnforced:false,
      downstreamActionAuthorized:false,recipientAccepted:false,projectImported:false,
      humanApprovalRequired:true,signed:false},
  };
  return{bytes,proposal,receipt};
}
const check=(receipt,bytes)=>inspectSupervisedReview(JSON.stringify(receipt),bytes,manifest,webcrypto);
describe('R13 browser-only supervised CAD receipt inspector',()=>{
  it('matches a digest-bound reviewed CAD fixture without elevating authority',async()=>{
    const f=await fixture();
    const r=await check(f.receipt,f.bytes);
    expect(r.sourceMatch).toBe(true);
    expect(r.authenticated).toBe(false);
    expect(r.recipientAccepted).toBe(false);
    expect(r.downstreamAuthorized).toBe(false);
    expect(manifest.summary.runtimeQualifiedModules).toBe(0);
  });
  it('rejects altered artifact, wrong source revision and fake downstream permissions',async()=>{
    const f=await fixture();
    const altered=new Uint8Array(f.bytes);altered[9]^=1;
    await expect(check(f.receipt,altered)).rejects.toThrow('SHA-256');
    await expect(check({...f.receipt,workflowSourceSha256:'a'.repeat(64)},f.bytes))
      .rejects.toThrow('different EVIE source');
    await expect(check({...f.receipt,governance:{...f.receipt.governance,recipientAccepted:true}},f.bytes))
      .rejects.toThrow('falsely claims');
  });
  it('rejects wrong blueprint geometry even with a matching recomputed digest',async()=>{
    const f=await fixture();
    f.proposal.project.walls[0].x2=2;
    const bytes=new TextEncoder().encode(JSON.stringify(f.proposal));
    const sha=Buffer.from(await webcrypto.subtle.digest('SHA-256',bytes)).toString('hex');
    await expect(check({...f.receipt,artifactSha256:sha,artifactBytes:bytes.length},bytes))
      .rejects.toThrow('geometry');
  });
});
