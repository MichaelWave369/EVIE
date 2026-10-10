/** R14 local-only content receipt check, not an authenticated production approval. */
const HEX = /^[0-9a-f]{64}$/;
const expected = {
  workflow:'local_content_hooks_review',
  module:'hooks_generator',
  schema:'evie.supervised-hooks-review/1',
};

export async function inspectHooksReceipt(receiptText, contentBytes, manifest, scriptBytes=null, provider=globalThis.crypto) {
  if(typeof receiptText!=='string'||new TextEncoder().encode(receiptText).length>32000)
    throw Error('Invalid or oversized receipt text.');
  const bytes=contentBytes instanceof Uint8Array?contentBytes:new Uint8Array(contentBytes);
  if(!bytes.byteLength||bytes.byteLength>32768)throw Error('Hook JSON must be under 32 KB.');
  let r, body;
  try{
    r=JSON.parse(receiptText);
    body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  }catch{throw Error('Invalid UTF-8 JSON review pair.');}
  if(!r||Array.isArray(r)||r.schemaVersion!==expected.schema||
    r.status!=='staged_for_human_review'||r.origin!=='local-unsigned-observation'||
    r.workflow!==expected.workflow||r.module!==expected.module)
    throw Error('Unsupported hook review receipt.');
  const gov=r.governance;
  if(!gov||gov.localModuleExecuted!==true||gov.legacyRunnerInvoked!==false||
    gov.databaseTouched!==false||gov.llmCalled!==false||
    gov.providerCredentialsProvided!==false||gov.externalPublishing!==false||
    gov.networkSandboxEnforced!==false||gov.authorizedForFutureRuns!==false||
    gov.humanReviewRequired!==true||gov.signed!==false)
    throw Error('Receipt improperly claims authority or execution safety.');
  const fixture=manifest.supervisedContentFixtures?.find(x=>x.workflow===expected.workflow&&x.module===expected.module);
  if(!fixture||!HEX.test(r.workflowSourceSha256)||
    r.workflowSourceSha256!==manifest.source?.sha256||
    r.moduleSourceSha256!==fixture.moduleSourceSha256||
    r.wrapperSourceSha256!==fixture.wrapperSourceSha256||
    r.workerSourceSha256!==fixture.workerSourceSha256)
    throw Error('Receipt does not match this published EVIE source version.');
  if(!provider?.subtle)throw Error('Browser crypto unavailable.');
  const digest=async input=>[...new Uint8Array(await provider.subtle.digest('SHA-256',input))]
    .map(n=>n.toString(16).padStart(2,'0')).join('');
  if(!HEX.test(r.artifactSha256)||r.artifactBytes!==bytes.byteLength||
     await digest(bytes)!==r.artifactSha256)
    throw Error('Hook JSON bytes do not match recorded SHA-256.');
  if(!body||Array.isArray(body)||body.topic!==r.topic||
     typeof r.topic!=='string'||r.topic.length>80||
     !Array.isArray(body.hooks)||body.hooks.length!==9||
     !body.hooks.every(h=>typeof h==='string'&&h.length>=3&&h.length<=1000)||
     !body.categories||Array.isArray(body.categories)||
     Object.keys(body.categories).sort().join(',')!=='controversial,curiosity,educational'||
     !['educational','controversial','curiosity'].every((name,i)=>{
       const start=i*3;return Array.isArray(body.categories[name])&&
         body.categories[name].length===3&&
         body.categories[name].every((h,j)=>h===body.hooks[start+j]);
     })||r.hookCount!==9||r.categoryCount!==3)
    throw Error('Generated content does not match the nine-hook contract.');
  if(scriptBytes){
    const script=scriptBytes instanceof Uint8Array?scriptBytes:new Uint8Array(scriptBytes);
    if(script.byteLength<20||script.byteLength>8192||!HEX.test(r.scriptSha256)||
       await digest(script)!==r.scriptSha256)
      throw Error('Original script does not match reported input digest.');
  }
  return {
    result:'matching_unsigned_hooks_review',topic:r.topic,hooks:body.hooks,
    categories:body.categories,artifactSha256:r.artifactSha256,
    sourceMatch:true,inputMatched:scriptBytes?true:null,
    authenticated:false,published:false,approved:false,
    note:'This is a matching unsigned local review. Hook claims require editorial fact checking. No publishing or verified remote execution.',
  };
}
