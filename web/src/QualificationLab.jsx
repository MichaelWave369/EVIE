import { useState } from 'react';
import manifest from './generated/mission-control.json';
import { examineLocalReceipt } from './receiptReview.js';
import './qualificationLab.css';

const CLI = 'python -m tools.evie_qualify run openblueprint_floor_plan --receipt ./cad-qualification.json';
const fixture = manifest.qualificationFixtures[0];

export default function QualificationLab() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const inspectFile = async event => {
    const file = event.target.files?.[0];
    event.target.value = '';
    setResult(null);
    setError('');
    if (!file) return;
    if (file.size > 64_000) {
      setError('Receipt exceeds the 64 KB inspection limit.');
      return;
    }
    try {
      const text = await file.text();
      const local = examineLocalReceipt(text, manifest);
      setResult(local);
      setMessage('Receipt reviewed in your browser. No file was uploaded or stored.');
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not inspect receipt.');
    }
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(CLI);
      setMessage('Local command copied.');
    } catch {
      setMessage('Clipboard unavailable. Select the command text manually.');
    }
  };
  return <div className="ql-page">
    <section className="ql-hero">
      <div className="mc-overline">EVIE / QUALIFICATION LAB / R7</div>
      <h2>Test. Record. <em>Trust cautiously.</em></h2>
      <p>Registration isn’t execution. This first qualification scenario runs one audited, deterministic CAD producer in a disposable local process. The public site never runs EVIE’s Python modules.</p>
    </section>
    <div className="ql-stats">
      <div><span>QUALIFICATION SCENARIOS</span><b>{manifest.qualificationFixtures.length}</b><small>Explicitly allowlisted</small></div>
      <div><span>PUBLIC LIVE QUALIFICATIONS</span><b>{manifest.summary.runtimeQualifiedModules}</b><small>No authenticated receipts</small></div>
      <div><span>PERMISSIONS GRANTED</span><b>00</b><small>Design and inspection only</small></div>
    </div>
    <section className="ql-allowlist">
      <div className="mc-overline">01 / AUDITED FIXTURE</div>
      <div className="ql-fixture-head">
        <div><h3>OpenBlueprint floor-plan producer</h3><p>Fixed 24 × 16 ft rectangular concept, one partition, door and network markers</p></div>
        <span className="mc-evidence mc-source"><i/> LOCAL TEST AVAILABLE</span>
      </div>
      <div className="ql-details">
        <div><small>REGISTERED MODULE</small><code>{fixture.module}</code></div>
        <div><small>SCENARIO</small><code>{fixture.scenario}</code></div>
        <div><small>PUBLIC SOURCE SHA-256</small><code>{fixture.sourceSha256.slice(0, 22)}…</code></div>
        <div><small>ISOLATION LIMIT</small><strong>No OS network sandbox</strong></div>
      </div>
      <div className="ql-command-label">RUN ON YOUR OWN EVIE MACHINE · REPO ROOT</div>
      <div className="ql-command"><code>{CLI}</code><button onClick={copy}>Copy command</button></div>
      <p className="ql-footnote">The command uses a separate Python process, strips provider credentials, checks actual CAD output and digest, then deletes temporary artifacts. It never asks your GitHub Page to reach your PC. It is not a hard sandbox.</p>
    </section>
    <section className="ql-inspector">
      <div className="mc-overline">02 / LOCAL RECEIPT INSPECTION</div>
      <h3>Inspect a qualification receipt</h3>
      <p>Choose a JSON receipt created by the local CLI. We'll compare its claimed source hash with this site's checked-in code and check its required fields. A self-reported file can be forged; matching a hash is not authentication.</p>
      <label className="ql-file-label">Select local receipt JSON
        <input type="file" accept=".json,application/json" onChange={inspectFile}/>
      </label>
      <div className="ql-no-upload">◉ Browser-only inspection · No upload · No storage · No API access</div>
      {error && <p role="alert" className="ql-error">{error}</p>}
      {message && <p role="status" className="ql-message">{message}</p>}
      {result ? <div className="ql-report">
        <div className="ql-result-title"><span>{result.status === 'pass' ? '✓' : '×'}</span>
          <div><b>{result.status === 'pass' ? 'Reported PASS' : 'Reported FAIL'}</b><small>Unsigned local observation · NOT authenticated</small></div>
        </div>
        <dl><dt>Module</dt><dd>{result.module}</dd>
          <dt>Scenario</dt><dd>{result.scenario}</dd>
          <dt>Source hash</dt><dd>Matches this public code snapshot</dd>
          <dt>Claimed checks</dt><dd>{result.checkCount} accepted</dd>
          <dt>Reported duration</dt><dd>{result.durationMs} ms</dd>
          <dt>Report date</dt><dd>{new Date(result.createdAt).toLocaleString()}</dd></dl>
        <p>**No official qualification was granted.** This file's claims remain untrusted until an independently authenticated replay or approved evidence channel exists.</p>
      </div> : <div className="ql-empty">No local receipt selected. Public qualification count remains zero.</div>}
    </section>
    <section className="ql-next"><div className="mc-overline">03 / NEXT GOVERNANCE GATE</div>
      <h3>From self-reported to reproducible evidence.</h3>
      <p>Before EVIE can automatically run additional modules, we need trusted receipts, version-bound replay, stronger isolation, explicit budgets and human approval for external effects. Especially publishing. Nobody needs an autonomous newsletter accident.</p>
    </section>
  </div>;
}
