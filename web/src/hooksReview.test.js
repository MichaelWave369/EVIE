import { describe,it,expect } from 'vitest';
import { webcrypto } from 'node:crypto';
import manifest from './generated/mission-control.json';
import { inspectHooksReceipt } from './hooksReview.js';

async function fixture(){
 const text='This editor workflow generates local hooks for a release and does not authorize any external publishing or subscriptions.';
 const script=new TextEncoder().encode(text);
 const hooks=Array.from({length:9},(_,i)=>'Local review hook number '+(i+1));
 const obj={topic:'EVIE Creator Loop',hooks,
   categories:{educational:hooks.slice(0,3),controversial:hooks.slice(3,6),curiosity:hooks.slice(6,9)}};
 const artifact=new TextEncoder().encode(JSON.stringify(obj));
 const sha=async b=>Buffer.from(await webcrypto.subtle.digest('SHA-256',b)).toString('hex');
 const source=manifest.supervisedContentFixtures[0];
 const receipt={schemaVersion:'evie.supervised-hooks-review/1',
   status:'staged_for_human_review',origin:'local-unsigned-observation',
   workflow:'local_content_hooks_review',module:'hooks_generator',topic:obj.topic,
   artifactSha256:await sha(artifact),artifactBytes:artifact.byteLength,
   scriptSha256:await sha(script),workflowSourceSha256:manifest.source.sha256,
   moduleSourceSha256:source.moduleSourceSha256,
   wrapperSourceSha256:source.wrapperSourceSha256,
   workerSourceSha256:source.workerSourceSha256,
   hookCount:9,categoryCount:3,
   governance:{localModuleExecuted:true,legacyRunnerInvoked:false,databaseTouched:false,
    llmCalled:false,providerCredentialsProvided:false,externalPublishing:false,
    networkSandboxEnforced:false,authorizedForFutureRuns:false,humanReviewRequired:true,signed:false}};
 return{artifact,receipt,script};
}
const inspect=(r,artifact,script)=>inspectHooksReceipt(JSON.stringify(r),artifact,manifest,script,webcrypto);
describe('R14 unsigned staged hooks browser inspector',()=>{
 it('matches nine real-format hooks while granting no publish permission',async()=>{
   const {artifact,receipt,script}=await fixture();
   const report=await inspect(receipt,artifact,script);
   expect(report.hooks).toHaveLength(9);
   expect(report.sourceMatch).toBe(true);
   expect(report.inputMatched).toBe(true);
   expect(report.authenticated).toBe(false);
   expect(report.published).toBe(false);
 });
 it('rejects altered file or source version',async()=>{
   const {artifact,receipt}=await fixture();
   const edited=new Uint8Array(artifact);edited[5]^=1;
   await expect(inspect(receipt,edited)).rejects.toThrow('SHA-256');
   await expect(inspect({...receipt,workflowSourceSha256:'a'.repeat(64)},artifact)).rejects.toThrow('source version');
 });
 it('refuses forged publishing permission or unverified inputs',async()=>{
   const {artifact,receipt}=await fixture();
   await expect(inspect({...receipt,governance:{...receipt.governance,externalPublishing:true}},artifact))
     .rejects.toThrow('authority');
   await expect(inspect(receipt,artifact,new TextEncoder().encode('This text is different from the original provided script and must not match')))
     .rejects.toThrow('input digest');
 });
 it('rejects category substitution even with newly calculated content digest',async()=>{
   const {artifact,receipt}=await fixture();
   const changed=JSON.parse(new TextDecoder().decode(artifact));
   changed.categories.educational[0]='fabricated content';
   const b=new TextEncoder().encode(JSON.stringify(changed));
   const sha=Buffer.from(await webcrypto.subtle.digest('SHA-256',b)).toString('hex');
   await expect(inspect({...receipt,artifactSha256:sha,artifactBytes:b.byteLength},b)).rejects.toThrow('nine-hook');
 });
});
