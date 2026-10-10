import { useState } from 'react';
import manifest from './generated/mission-control.json';
import { inspectSupervisedReview } from './supervisedReview.js';
import './supervisedCad.css';

const RUN_COMMAND = 'python -m tools.evie_supervised run openblueprint_concept_floor_plan --stage-dir ../evie-cad-review-001 --confirm-local-execution';

export default function SupervisedCad() {
  const [receipt,setReceipt]=useState(null);
  const [artifact,setArtifact]=useState(null);
  const [result,setResult]=useState(null);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [loading,setLoading]=useState(false);
  const select=(setter,e)=>{setter(e.target.files?.[0]||null);setResult(null);setError('');setNotice('')};
  const copy=async()=>{
    try{await navigator.clipboard.writeText(RUN_COMMAND);setNotice('Copied. Choose a NEW output folder each run.');}
    catch{setNotice('Clipboard unavailable; select and copy the command text manually.');}
  };
  const inspect=async()=>{
    if(!receipt||!artifact)return;
    setResult(null);setError('');setLoading(true);
    try{
      if(receipt.size>32_000||artifact.size>64_000)throw Error('Review files exceed 32 KB / 64 KB limits.');
      const answer=await inspectSupervisedReview(await receipt.text(),await artifact.arrayBuffer(),manifest);
      setResult(answer);setNotice('Files checked in this browser only. No upload or import occurred.');
    }catch(e){setError(e instanceof Error?e.message:'Review files rejected.');}
    finally{setLoading(false);}
  };
  return <section className="sc-root">
    <div className="mc-overline">R13 / FIRST LOCAL WORKFLOW EXECUTION / ONE FIXED CAD STEP</div>
    <header className="sc-head"><div><h3>Supervised CAD run</h3>
      <p>Ready to go beyond planning? This local command runs one precisely fixed 24 × 16 ft EVIE floor-plan fixture, validates the output, then stages review files to a new folder outside your Git checkout.</p>
    </div><span>LOCAL OPT-IN ONLY</span></header>
    <div className="sc-rules"><span>1 ALLOWLISTED WORKFLOW</span><span>20s TIME LIMIT</span><span>64 KB ARTIFACT CAP</span><span>NO AUTO-IMPORT</span></div>
    <div className="sc-command"><span>RUN ON YOUR OWN PC · EVIE REPO ROOT</span>
      <code>{RUN_COMMAND}</code>
      <button onClick={copy}>Copy local command ↗</button>
    </div>
    <p className="sc-caution">The command requires <code>--confirm-local-execution</code> and refuses existing output folders. It runs only this one fixed scenario. Its Python subprocess is <strong>not</strong> a hard OS or network sandbox, so only run a checkout you trust. GitHub Pages cannot run it remotely.</p>
    <div className="mc-overline">INSPECT TWO REVIEW FILES AFTER THE LOCAL RUN</div>
    <div className="sc-files">
      <label>01 / review-receipt.json
        <input type="file" accept=".json,application/json" onChange={e=>select(setReceipt,e)}/>
      </label>
      <label>02 / openblueprint.evie-proposal.json
        <input type="file" accept=".json,application/json" onChange={e=>select(setArtifact,e)}/>
      </label>
    </div>
    <button className="sc-inspect" onClick={inspect} disabled={!receipt||!artifact||loading}>
      {loading?'Checking exact bytes…':'Inspect staged CAD review pair →'}
    </button>
    {error&&<p className="sc-error" role="alert">{error}</p>}
    {notice&&<p className="sc-notice" role="status">{notice}</p>}
    {result&&<div className="sc-report"><strong>✓ Staged file pair matches the fixed CAD scenario</strong>
      <div><span>{result.wallCount} walls</span><span>{result.symbolCount} symbols</span><span>SHA-256 matches</span><span>Source version matches</span></div>
      <p>Unsigned local observation. The file is <strong>not authenticated, not imported, and not approved by OpenBlue</strong>. OpenBlue's own preview and approval are separate actions.</p>
      <a href="https://michaelwave369.github.io/OpenBlueprintStudio/" target="_blank" rel="noreferrer">
        Open OpenBlue for separate manual review ↗</a>
    </div>}
  </section>;
}
