/** R13: browser-only check of unsigned staged CAD review files.
 * Not a proof of who ran the fixture, not recipient approval, never a job gate.
 */
const HEX = /^[a-f0-9]{64}$/;
const WORKFLOW = 'openblueprint_concept_floor_plan';
const MODULE = 'openblueprint_floor_plan';
const WALLS = [
  [0, 0, 24, 0], [24, 0, 24, 16], [24, 16, 0, 16],
  [0, 16, 0, 0], [12, 0, 12, 16],
];

export async function inspectSupervisedReview(receiptText, artifactBytes, manifest, cryptoProvider=globalThis.crypto) {
  if(typeof receiptText!=='string'||new TextEncoder().encode(receiptText).length>32_000)
    throw Error('Review receipt must be JSON under 32 KB.');
  const bytes = artifactBytes instanceof Uint8Array?artifactBytes:new Uint8Array(artifactBytes);
  if(!bytes.length||bytes.length>64_000) throw Error('Staged CAD proposal exceeds 64 KB.');
  let receipt, proposal;
  try {
    receipt=JSON.parse(receiptText);
    proposal=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  } catch {throw Error('Invalid UTF-8 JSON review bundle.');}
  if(!receipt||Array.isArray(receipt)||receipt.schemaVersion!=='evie.supervised-cad-review/1'||
     receipt.status!=='staged_for_human_review'||receipt.workflow!==WORKFLOW||
     receipt.module!==MODULE||receipt.scenario!=='cad_supervised_24x16_v1'||
     receipt.origin!=='local-unsigned-observation')
    throw Error('Unsupported supervised review receipt.');
  const gov=receipt.governance;
  if(!gov||gov.localFixtureExecuted!==true||gov.legacyRunnerInvoked!==false||
     gov.databaseTouched!==false||gov.providerCredentialsProvided!==false||
     gov.networkSandboxEnforced!==false||gov.downstreamActionAuthorized!==false||
     gov.recipientAccepted!==false||gov.projectImported!==false||
     gov.humanApprovalRequired!==true||gov.signed!==false)
    throw Error('Receipt falsely claims import, trust or execution permission.');
  if(!receipt.evidence||!Object.values(receipt.evidence).every(value=>value===true)||
     receipt.evidence.fixedWorkflowStepsMatched!==true||
     receipt.evidence.proposalSchemaValidated!==true||
     receipt.evidence.outputDigestVerified!==true||
     receipt.evidence.geometryVerified!==true)
    throw Error('Missing expected fixture observations.');
  const producer=manifest.qualificationFixtures?.find(f=>f.module===MODULE);
  if(!HEX.test(receipt.workflowSourceSha256)||receipt.workflowSourceSha256!==manifest.source?.sha256||
     !HEX.test(receipt.producerSourceSha256)||receipt.producerSourceSha256!==producer?.sourceSha256)
    throw Error('Staged receipt is from a different EVIE source revision.');
  if(!cryptoProvider?.subtle)throw Error('SHA-256 unavailable in this browser.');
  const digest = Array.from(new Uint8Array(await cryptoProvider.subtle.digest('SHA-256',bytes)))
    .map(x=>x.toString(16).padStart(2,'0')).join('');
  if(receipt.artifactBytes!==bytes.length||!HEX.test(receipt.artifactSha256)||
     receipt.artifactSha256!==digest)throw Error('Staged artifact bytes or SHA-256 do not match receipt.');
  const project=proposal?.project;
  if(proposal.schemaVersion!=='openblueprint.evie-proposal/1'||
     proposal.source?.system!=='EVIE'||proposal.source?.cardId!==MODULE||
     proposal.source.mode!=='generated'||proposal.source.runId!==receipt.producerRunId||
     project?.schemaVersion!=='openblueprint.project/1'||
     project?.metadata?.units!=='ft'||!Array.isArray(project.walls)||
     !Array.isArray(project.symbols)||
     project.walls.length!==5||project.symbols.length!==2||
     receipt.walls!==5||receipt.symbols!==2||receipt.units!=='ft')
    throw Error('Staged artifact schema or producer identity mismatch.');
  if(!project.walls.every((w,i)=>
      ['x1','y1','x2','y2'].every((key,k)=>w[key]===WALLS[i][k])&&
      typeof w.id==='string'&&Number.isFinite(w.height)&&w.height>0&&
      Number.isFinite(w.thickness)&&w.thickness>0))
    throw Error('Staged CAD geometry does not match the fixed scenario.');
  if(new Set([...project.walls,...project.symbols].map(x=>x.id)).size!==7||
     !project.symbols.every(s=>['door','network'].includes(s.type))||
     new Set(project.symbols.map(s=>s.type)).size!==2)
    throw Error('Staged symbol types or IDs are invalid.');
  return {
    result:'matching_unsigned_local_cad_review',
    workflow:WORKFLOW,wallCount:5,symbolCount:2,
    artifactSha256:digest,sourceMatch:true,bytesMatch:true,
    signed:false,authenticated:false,recipientAccepted:false,
    projectImported:false,downstreamAuthorized:false,
    note:'Matching unsigned local review receipt; not independent proof of execution, host integrity or OpenBlue acceptance.',
  };
}
