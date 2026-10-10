/** R15: local four-file workflow handoff inspector.
 * Matching files do not prove who invoked either process or that a human approved claims.
 */
import {inspectHooksReceipt} from './hooksReview.js';
const SHA=/^[0-9a-f]{64}$/;

export async function inspectDistributionChain(firstReceiptText,firstBytes,secondReceiptText,secondBytes,manifest,cryptoProvider=globalThis.crypto){
  const first=await inspectHooksReceipt(firstReceiptText,firstBytes,manifest,null,cryptoProvider);
  if(typeof secondReceiptText!=='string'||new TextEncoder().encode(secondReceiptText).length>32000)
    throw Error('Distribution receipt exceeds 32 KB limit.');
  const output=secondBytes instanceof Uint8Array?secondBytes:new Uint8Array(secondBytes);
  if(!output.byteLength||output.byteLength>32768)throw Error('Distribution JSON exceeds 32 KB limit.');
  let receipt,body;
  try {
    receipt=JSON.parse(secondReceiptText);
    body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(output));
  }catch {throw Error('Malformed distribution JSON or receipt.');}
  if(!receipt||Array.isArray(receipt)||
      receipt.schemaVersion!=='evie.supervised-distribution-review/1'||
      receipt.workflow!=='local_hooks_to_distribution_review'||
      receipt.completedStage!=='distribution_generator'||
      receipt.status!=='staged_for_human_review'||
      receipt.origin!=='local-unsigned-observation'||receipt.topic!==first.topic)
    throw Error('Unsupported R15 distribution receipt.');
  const g=receipt.governance;
  if(!g||g.operatorConfirmedExactDigest!==true||g.operatorIdentityVerified!==false||
     g.humanSignatureVerified!==false||g.localSecondModuleExecuted!==true||
     g.legacyRunnerInvoked!==false||g.databaseTouched!==false||
     g.llmCalled!==false||g.providerCredentialsProvided!==false||
     g.externalPublishing!==false||g.networkSandboxEnforced!==false||
     g.furtherExecutionAuthorized!==false||g.editorialApprovalGranted!==false||
     g.signed!==false)
    throw Error('R15 receipt claims unsupported execution or editorial authority.');
  const source=manifest.supervisedDistributionFixtures?.find(x=>
     x.workflow==='local_hooks_to_distribution_review'&&x.module==='distribution_generator');
  if(!source||receipt.workflowSourceSha256!==manifest.source?.sha256||
     !SHA.test(receipt.distributionSourceSha256)||
     receipt.distributionSourceSha256!==source.moduleSourceSha256||
     receipt.distributionWrapperSha256!==source.wrapperSourceSha256||
     receipt.workerSourceSha256!==source.workerSourceSha256)
    throw Error('R15 local source revision does not match this published site.');
  const digest=bytes=>cryptoProvider.subtle.digest('SHA-256',bytes).then(b=>
     [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join(''));
  if(receipt.approvedInputSha256!==first.artifactSha256)
    throw Error('Second-stage approved input digest does not match first-stage hooks.');
  if(receipt.distributionBytes!==output.byteLength||
     !SHA.test(receipt.distributionSha256)||
     await digest(output)!==receipt.distributionSha256)
    throw Error('Distribution artifact digest or byte count mismatch.');
  if(!body||Array.isArray(body)||body.topic!==first.topic||
     !Array.isArray(body.hooks_used)||!Array.isArray(body.tiktok_hooks)||
     body.hooks_used.length!==5||body.tiktok_hooks.length!==5||
     !body.hooks_used.every((h,i)=>h===first.hooks[i])||
     !body.tiktok_hooks.every((h,i)=>h===first.hooks[i])||
     !Array.isArray(body.twitter_thread)||body.twitter_thread.length<1||
     receipt.hooksConsumed!==5)
    throw Error('Second-stage distribution content does not consume the approved five hooks.');
  return {
    status:'matching_unsigned_two_stage_review',
    topic:first.topic,
    approvedInputSha256:first.artifactSha256,
    distributionSha256:receipt.distributionSha256,
    hooksUsed:body.hooks_used,
    tweetThread:body.twitter_thread,
    sourceMatched:true,
    operatorIdentityVerified:false,
    editoriallyApproved:false,
    published:false,
    downstreamAuthorized:false,
  };
}
