import { useState } from 'react';
import { inspectLocalOpenBlueFiles } from './openBluePreflight.js';
import OpenBlueReplayReceipt from './OpenBlueReplayReceipt.jsx';
import './openBlueInspector.css';

const OPENBLUE_URL = 'https://michaelwave369.github.io/OpenBlueprintStudio/';
export default function OpenBlueInspector() {
  const [review, setReview] = useState(null);
  const [blueprint, setBlueprint] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const choose = (setter, event) => {
    setter(event.target.files?.[0] || null);
    setResult(null);
    setError('');
  };
  const run = async () => {
    if (!review || !blueprint) return;
    setRunning(true);
    setError('');
    setResult(null);
    try { setResult(await inspectLocalOpenBlueFiles(review, blueprint)); }
    catch(e) { setError(e instanceof Error ? e.message : 'Could not inspect the selected files.'); }
    finally { setRunning(false); }
  };
  return <section className="ob-inspector">
    <div className="fg-overline">R9 / OPENBLUE FILE RECEIVER PREFLIGHT</div>
    <div className="ob-head">
      <div><h3>OpenBlue handoff check</h3>
      <p>Two matching files, one check. Verify a family review envelope against the actual OpenBlue proposal bytes and its geometry before you choose to import the blueprint.</p></div>
      <span className="ob-status">READ-ONLY · NO TRANSFER</span>
    </div>
    <div className="ob-steps">
      <label><b>01</b><span>EVIE family review JSON</span>
        <input type="file" accept=".json,application/json" onChange={e=>choose(setReview,e)}/>
        {review&&<small>{review.name} · {review.size.toLocaleString()} bytes</small>}
      </label>
      <label><b>02</b><span>OpenBlue proposal JSON</span>
        <input type="file" accept=".json,application/json" onChange={e=>choose(setBlueprint,e)}/>
        {blueprint&&<small>{blueprint.name} · {blueprint.size.toLocaleString()} bytes</small>}
      </label>
    </div>
    <button className="ob-check" disabled={!review||!blueprint||running} onClick={run}>
      {running?'Validating locally…':'Check exact bytes, expiry and plan geometry →'}
    </button>
    <p className="ob-notice">Files stay on this device. The review proposal expires after 1–30 minutes; create a new one if the old envelope is stale. No API keys, agents, network calls or project modifications.</p>
    {error&&<div className="ob-failure" role="alert"><strong>Preflight rejected</strong><p>{error}</p><small>Nothing was imported or changed.</small></div>}
    {result&&<div className="ob-success" role="status"><strong>✓ Local preflight passed</strong>
      <div className="ob-results">
        <span>Units <b>{result.units}</b></span>
        <span>Walls <b>{result.walls}</b></span>
        <span>Symbols <b>{result.symbols}</b></span>
        <span>SHA-256 <b>Match</b></span>
        <span>Mode <b>{result.sourceMode}</b></span>
        <span>Recipient accepted <b>NO</b></span>
      </div>
      <p>This is not an OpenBlue acceptance receipt. Your file still requires import, preview and explicit approval inside OpenBlue. An unsigned matching pair can be forged together.</p>
      <a href={OPENBLUE_URL} target="_blank" rel="noreferrer">Open OpenBlue Studio for manual import ↗</a>
      <OpenBlueReplayReceipt preflight={result}/>
    </div>}
  </section>;
}
