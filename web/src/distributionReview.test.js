import {describe,it,expect} from 'vitest';
import {webcrypto} from 'node:crypto';
import manifest from './generated/mission-control.json';
import {inspectDistributionChain} from './distributionReview.js';

async function fixtures(){
  const sha=async bytes=>Buffer.from(await webcrypto.subtle.digest('SHA-256',bytes)).toString('hex');
  const hooks=Array.from({length:9},(_,i)=>'Locally reviewed draft hook number '+(i+1));
  const first={topic:'EVIE Creator Loop',hooks,
    categories:{educational:hooks.slice(0,3),controversial:hooks.slice(3,6),curiosity:hooks.slice(6)}};
  const b1=new TextEncoder().encode(JSON.stringify(first));
  const r1={
    schemaVersion:'evie.supervised-hooks-review/1',status:'staged_for_human_review',
    origin:'local-unsigned-observation',workflow:'local_content_hooks_review',
    module:'hooks_generator',topic:first.topic,
    workflowSourceSha256:manifest.source.sha256,
    moduleSourceSha256:manifest.supervisedContentFixtures[0].moduleSourceSha256,
    wrapperSourceSha256:manifest.supervisedContentFixtures[0].wrapperSourceSha256,
    workerSourceSha256:manifest.supervisedContentFixtures[0].workerSourceSha256,
    artifactSha256:await sha(b1),artifactBytes:b1.byteLength,
    hookCount:9,categoryCount:3,
    governance:{localModuleExecuted:true,legacyRunnerInvoked:false,
      databaseTouched:false,llmCalled:false,providerCredentialsProvided:false,
      externalPublishing:false,networkSandboxEnforced:false,
      authorizedForFutureRuns:false,humanReviewRequired:true,signed:false}};
  const second={topic:first.topic,hooks_used:hooks.slice(0,5),tiktok_hooks:hooks.slice(0,5),
    twitter_thread:['1/ Write local notes','2/ Review content'],generated_at:'2026-10-09T00:00:00Z'};
  const b2=new TextEncoder().encode(JSON.stringify(second));
  const r2={
    schemaVersion:'evie.supervised-distribution-review/1',
    status:'staged_for_human_review',workflow:'local_hooks_to_distribution_review',
    completedStage:'distribution_generator',origin:'local-unsigned-observation',
    topic:first.topic,approvedInputSha256:await sha(b1),
    distributionSha256:await sha(b2),distributionBytes:b2.length,
    hooksConsumed:5,workflowSourceSha256:manifest.source.sha256,
    distributionSourceSha256:manifest.supervisedDistributionFixtures[0].moduleSourceSha256,
    distributionWrapperSha256:manifest.supervisedDistributionFixtures[0].wrapperSourceSha256,
    workerSourceSha256:manifest.supervisedDistributionFixtures[0].workerSourceSha256,
    governance:{operatorConfirmedExactDigest:true,operatorIdentityVerified:false,
      humanSignatureVerified:false,localSecondModuleExecuted:true,
      legacyRunnerInvoked:false,databaseTouched:false,llmCalled:false,
      providerCredentialsProvided:false,externalPublishing:false,
      networkSandboxEnforced:false,furtherExecutionAuthorized:false,
      editorialApprovalGranted:false,signed:false}};
  return{b1,b2,r1,r2};
}
const check=f=>inspectDistributionChain(JSON.stringify(f.r1),f.b1,
  JSON.stringify(f.r2),f.b2,manifest,webcrypto);
describe('R15 browser two-stage offline receipt inspector',()=>{
  it('verifies actual input→output hook content, but never authorization',async()=>{
    const f=await fixtures(), result=await check(f);
    expect(result.status).toBe('matching_unsigned_two_stage_review');
    expect(result.hooksUsed).toHaveLength(5);
    expect(result.published).toBe(false);
    expect(result.editoriallyApproved).toBe(false);
    expect(result.operatorIdentityVerified).toBe(false);
    expect(result.downstreamAuthorized).toBe(false);
  });
  it('rejects unapproved input digest or changed output bytes',async()=>{
    const f=await fixtures();
    await expect(check({...f,r2:{...f.r2,approvedInputSha256:'b'.repeat(64)}}))
      .rejects.toThrow('approved input digest');
    const changed=new Uint8Array(f.b2);const pos=new TextDecoder().decode(changed).indexOf('Write');expect(pos).toBeGreaterThan(0);changed[pos]='S'.charCodeAt(0);
    await expect(check({...f,b2:changed})).rejects.toThrow('digest');
  });
  it('rejects source mismatch and inflated authority',async()=>{
    const f=await fixtures();
    await expect(check({...f,r2:{...f.r2,workflowSourceSha256:'a'.repeat(64)}}))
      .rejects.toThrow('source revision');
    await expect(check({...f,r2:{...f.r2,governance:{...f.r2.governance,editorialApprovalGranted:true}}}))
      .rejects.toThrow('authority');
  });
  it('rejects changed first five hooks even with correctly recomputed artifact hash',async()=>{
    const f=await fixtures();
    const body=JSON.parse(new TextDecoder().decode(f.b2));
    body.hooks_used[0]='Unapproved content';
    const b=new TextEncoder().encode(JSON.stringify(body));
    const digest=Buffer.from(await webcrypto.subtle.digest('SHA-256',b)).toString('hex');
    await expect(check({...f,b2:b,r2:{...f.r2,distributionSha256:digest,distributionBytes:b.length}}))
      .rejects.toThrow('approved five hooks');
  });
});
