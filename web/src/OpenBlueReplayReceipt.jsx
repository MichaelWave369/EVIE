import { useState } from 'react';
import { checkReplayReport } from './openBlueReplayReview.js';

const SAMPLE = 'node tools/openblue_parser_replay.mjs --openblue-dir ../OpenBlueprintStudio --expected-revision YOUR_VERIFIED_COMMIT_SHA --proposal ./review.proposal.json --artifact ./plan.json --receipt ./openblue-parser-replay.json';
export default function OpenBlueReplayReceipt({ preflight }) {
  const [report,setReport]=useState(null);
  const [error,setError]=useState('');
  const [message,setMessage]=useState('');
  const [busy,setBusy]=useState(false);
  const inspect=async event=>{
    const file=event.target.files?.[0];
    event.target.value='';
    setReport(null);setError('');
    if(!file)return;
    if(file.size>32_000){setError('Replay report is over the 32 KB limit.');return;}
    setBusy(true);
    try {
      const reviewed=checkReplayReport(await file.text(),preflight);
      setReport(reviewed);
    }catch(e){setError(e instanceof Error?e.message:'Invalid replay report.');}
    finally{setBusy(false);}
  };
  const copy=async()=>{
    try{await navigator.clipboard.writeText(SAMPLE);setMessage('Command copied. Replace the commit placeholder with your trusted local OpenBlue HEAD.');}
    catch{setMessage('Clipboard unavailable; select the command manually.');}
  };
  return <div className="obr-panel">
    <div className="fg-overline">R10 / PARSER REPLAY / REPRODUCIBLE CONTRACT TEST</div>
    <h4>Check OpenBlue's actual parser</h4>
    <p>This optional test invokes the real <code>parseEvieProposal</code> from a deliberately chosen local OpenBlue checkout. It is <strong>not</strong> a browser import, and it runs trusted local JavaScript, so use only a repository revision you trust.</p>
    <div className="obr-command"><code>{SAMPLE}</code><button onClick={copy}>Copy local command</button></div>
    <p>Get your exact commit SHA with <code>git -C ../OpenBlueprintStudio rev-parse HEAD</code>. The CLI refuses changes to selected parser files and rejects any revision mismatch. It never writes into OpenBlue.</p>
    <div className="obr-file">
      <label>Inspect optional unsigned parser replay receipt
        <input type="file" accept=".json,application/json" onChange={inspect} disabled={busy}/>
      </label>
    </div>
    {message&&<p role="status" className="obr-message">{message}</p>}
    {error&&<p role="alert" className="obr-error">{error}</p>}
    {report&&<div className="obr-match" role="status">
      <b>Matching unsigned local parser replay report</b>
      <p>Receipt fields match this browser's preflight: {report.walls} walls, {report.symbols} symbols. Reported OpenBlue source revision: <code>{report.operatorSelectedRevision}</code>.</p>
      <strong>Not authenticated · Not imported · Not approved</strong>
      <p>The JSON may be forged. Compare source revisions and rerun the parser independently before trusting it.</p>
    </div>}
  </div>;
}
