import {useState} from 'react';
import manifest from './generated/mission-control.json';
import {inspectDistributionChain} from './distributionReview.js';
import SignedLeaseGuide from './SignedLeaseGuide.jsx';
import DockerIsolationGuide from './DockerIsolationGuide.jsx';
import GovernedFlowGuide from './GovernedFlowGuide.jsx';
import CompletionLedgerGuide from './CompletionLedgerGuide.jsx';
import SafeEntryGuide from './SafeEntryGuide.jsx';
import './distributionStudio.css';
const FIRST='python -m tools.evie_supervised_hooks local_content_hooks_review --script-file ./draft.txt --topic "EVIE Creator Loop" --stage-dir ../evie-hooks-review-001 --confirm-local-execution';
const SECOND='python -m tools.evie_supervised_distribution --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --confirm-local-execution';

export default function DistributionStudio(){
  const [files,setFiles]=useState({});
  const [report,setReport]=useState(null);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [busy,setBusy]=useState(false);
  const update=(key,event)=>{setFiles(old=>({...old,[key]:event.target.files?.[0]||null}));setReport(null);setError('');};
  const copy=async command=>{
    try{await navigator.clipboard.writeText(command);setNotice('Command copied. Edit paths and explicitly replace the SHA-256 placeholder after reviewing Stage 1.');}
    catch{setNotice('Clipboard unavailable; select command manually.');}
  };
  const inspect=async()=>{
    setBusy(true);setReport(null);setError('');
    try{
      if(!files.firstReceipt||!files.hooks||!files.secondReceipt||!files.distribution)
        throw Error('All four review files are required.');
      if(files.firstReceipt.size>32000||files.secondReceipt.size>32000||
         files.hooks.size>32768||files.distribution.size>32768)
        throw Error('Selected file exceeds review limit.');
      const result=await inspectDistributionChain(
        await files.firstReceipt.text(),await files.hooks.arrayBuffer(),
        await files.secondReceipt.text(),await files.distribution.arrayBuffer(),
        manifest);
      setReport(result);setNotice('All comparisons happened locally in this browser. No publishing or API calls.');
    }catch(e){setError(e instanceof Error?e.message:'Cannot inspect local review chain.');}
    finally{setBusy(false);}
  };
  return <section className="ds-root">
    <div className="mc-overline">R15 / HOOKS → DISTRIBUTION / TWO REAL MODULES</div>
    <header><h3>Content Handoff Studio</h3>
      <p>The original two-stage content handoff remains available for compatibility. For NEW runs, prefer the R21 EVIE Safe Entry guide below: both stages use offline Docker and the second requires separate signed approval.</p>
    </header>
    <SafeEntryGuide/>
    <div className="ds-boundary">LEGACY DIRECT TWO-COMMAND PATH · COMPATIBILITY ONLY · SHA-PINNED REVIEW · NO PUBLISHING</div>
    <p className="ds-caution">The commands in the next two cards are older direct R14/R15 commands. They run host Python, have weaker protections, and are NOT the recommended default. Keep them only for existing compatibility workflows.</p>
    <div className="ds-stages">
      <div><strong>01 / Produce & review nine hooks</strong><p>Use the existing R14 real module. Read and edit claims before deciding to continue. The next step validates the exact saved JSON bytes.</p>
        <div className="ds-command"><code>{FIRST}</code><button onClick={()=>copy(FIRST)}>Copy step 1</button></div>
      </div>
      <div><strong>02 / Confirm hash & draft distribution</strong><p>Open the first stage's <code>review-receipt.json</code>. Only after inspecting the nine hooks, substitute its <code>artifactSha256</code> into the second command. This isn't a cryptographic human signature.</p>
        <div className="ds-command"><code>{SECOND}</code><button onClick={()=>copy(SECOND)}>Copy step 2</button></div>
      </div>
    </div>
    <p className="ds-caution">The second command refuses a mismatched SHA-256, invalid R14 receipt, wrong source revision, unsupported workflow, or existing output folder. It executes the real local DistributionGenerator in a temporary subprocess, <strong>not an OS sandbox</strong>. Its marketing wording is a draft and may be misleading. Edit before external use.</p>
    <div className="mc-overline">03 / BROWSER-ONLY FOUR-FILE INSPECTION</div>
    <div className="ds-uploads">{[
      ['firstReceipt','R14 review-receipt.json'],
      ['hooks','R14 nine-hooks.json'],
      ['secondReceipt','R15 distribution-review-receipt.json'],
      ['distribution','R15 distribution-draft.json'],
    ].map(([key,label])=><label key={key}>{label}<input type="file" accept=".json,application/json" onChange={e=>update(key,e)}/></label>)}</div>
    <button className="ds-inspect" disabled={busy||Object.values(files).filter(Boolean).length<4} onClick={inspect}>{busy?'Checking locally…':'Inspect both receipts and actual hook handoff →'}</button>
    {error&&<p className="ds-error" role="alert">{error}</p>}
    {notice&&<p className="ds-notice" role="status">{notice}</p>}
    {report&&<div className="ds-result"><strong>✓ Both local artifact receipts match</strong>
      <p>First five reviewed hooks were actually found in the downstream distribution draft. Matching these unsigned files does not authenticate who ran either step, prove source execution independently, or approve a post.</p>
      <ol>{report.hooksUsed.map((h,i)=><li key={i}>{h}</li>)}</ol>
      <div className="ds-deny">OPERATOR ID UNVERIFIED · EDITORIAL APPROVAL PENDING · NOTHING PUBLISHED</div>
    </div>}
    <SignedLeaseGuide/>
    <DockerIsolationGuide/>
    <GovernedFlowGuide/>
    <CompletionLedgerGuide/>
  </section>;
}
