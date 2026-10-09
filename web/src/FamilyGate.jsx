import { useState } from 'react';
import targets from './generated/family-targets.json';
import { reviewLocalArtifact, exportProposal, MAX_ARTIFACT_BYTES } from './familyGateLogic.js';
import OpenBlueInspector from './OpenBlueInspector.jsx';
import './familyGate.css';

const COMMANDS = [
  'python -m tools.evie_family_gate catalog',
  'python -m tools.evie_family_gate prepare --target openblue --kind openblueprint.evie-proposal/1 --artifact ./your-plan.json --proposal ./handoff.proposal.json',
  'python -m tools.evie_family_gate acknowledge --proposal ./handoff.proposal.json --signing-key ./evie-local.pem --ack ./handoff.ack.json',
  'python -m tools.evie_family_gate verify --ack ./handoff.ack.json --trusted-public ./evie-trusted.pub.pem',
];
function Icon({id}){return <span className="fg-icon">{({openblue:'⌗',fielddeck:'▦',phios:'◈',superphivessel:'Φ',pixelforge:'⬡',domistika:'✧'})[id]}</span>}
export default function FamilyGate() {
  const [target, setTarget] = useState('openblue');
  const [file, setFile] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const selected = targets.targets.find(t=>t.id===target);
  const changeTarget = id => {setTarget(id);setProposal(null);setError('');setFeedback('')};
  const changeFile = e => {setFile(e.target.files?.[0]||null);setProposal(null);setError('');setFeedback('')};
  const generate = async () => {
    if(!file) return;
    setBusy(true);setError('');setProposal(null);
    try {
      const record = await reviewLocalArtifact(file,target,targets);
      setProposal(record);
      setFeedback('Local hash and short-lived proposal created. No recipient was contacted.');
    } catch(e) {setError(e instanceof Error?e.message:'Cannot prepare the proposal');}
    finally {setBusy(false);}
  };
  const copy = async command => {
    try {await navigator.clipboard.writeText(command);setFeedback('Command copied for local use.')}
    catch {setFeedback('Clipboard unavailable. Select the command manually.')}
  };
  return <div className="fg-page">
    <header className="fg-hero"><div className="fg-overline">EVIE COMMONS / FAMILY PERMISSION GATE / R8B</div>
      <h1>Build bridges.<br/><em>Keep the keys.</em></h1>
      <p>Six planned connections across the family. Prepare a bounded, digest-linked artifact review without opening APIs, sending files, or giving agents permission to act.</p>
      <div className="fg-stats"><span><b>{targets.targets.length}</b> proposed routes</span><span><b>0</b> transports live</span><span><b>0</b> runtime grants</span></div>
    </header>
    <div className="fg-alert"><b>◇ CONTRACTS, NOT CONNECTORS.</b> These routes describe intended artifact formats only. No target app has been verified as connected by this feature. Review acknowledgement is not execution authority.</div>
    <div className="fg-title"><span>01 / FAMILY TARGETS</span><h2>Where EVIE could connect.</h2></div>
    <div className="fg-targets">{targets.targets.map(t=><button key={t.id} onClick={()=>changeTarget(t.id)} className={'fg-target '+(target===t.id?'chosen':'')}>
      <div className="fg-target-top"><Icon id={t.id}/><span>{target===t.id?'SELECTED':'↗'}</span></div>
      <h3>{t.label}</h3><p>{t.description}</p><small>NO TRANSPORT · NO EXECUTION</small>
    </button>)}</div>
    <div className="fg-title"><span>02 / LOCAL ARTIFACT REVIEW</span><h2>Prepare a handoff envelope.</h2></div>
    <section className="fg-workshop"><div className="fg-editor">
      <div className="fg-field"><label htmlFor="fg-target">INTENDED RECIPIENT</label><select id="fg-target" value={target} onChange={e=>changeTarget(e.target.value)}>{targets.targets.map(t=><option key={t.id} value={t.id}>{t.label}</option>)}</select></div>
      <div className="fg-field"><label>EXPECTED ARTIFACT KIND</label><code>{selected.artifactKinds[0]}</code></div>
      <div className="fg-field"><label htmlFor="fg-file">SELECT LOCAL FILE (MAX 8 MB)</label><input id="fg-file" type="file" onChange={changeFile}/></div>
      {file&&<p className="fg-file">Selected: {file.name} · {file.size.toLocaleString()} bytes</p>}
      <button disabled={!file||busy||file.size>MAX_ARTIFACT_BYTES} className="fg-create" onClick={generate}>{busy?'Checking locally…':'Prepare review proposal →'}</button>
      <p className="fg-info">This browser calculates a SHA-256 digest and creates a 15-minute review envelope. It never inspects the file's intended engineering or application correctness, and never uploads its contents.</p>
      {error&&<p role="alert" className="fg-error">{error}</p>}
      {feedback&&<p role="status" className="fg-feedback">{feedback}</p>}
    </div><div className="fg-preview">
      <div className="fg-preview-top"><b>Review envelope</b><span>LOCAL ONLY</span></div>
      {proposal?<><dl>
          <dt>Recipient</dt><dd>{proposal.target}</dd>
          <dt>Format</dt><dd>{proposal.artifactKind}</dd>
          <dt>Artifact SHA-256</dt><dd><code>{proposal.artifactSha256}</code></dd>
          <dt>Expires</dt><dd>{new Date(proposal.expiresAt).toLocaleString()}</dd>
          <dt>Requested effects</dt><dd>NONE</dd>
          <dt>Automatic transfer</dt><dd>DISABLED</dd>
          <dt>Execution permission</dt><dd>NONE</dd>
        </dl><button className="fg-export" onClick={()=>exportProposal(proposal)}>↓ Download review-only JSON</button></>
        :<div className="fg-empty"><strong>◇</strong><span>No review proposal prepared yet. Select a local artifact and target above.</span></div>}
    </div></section>
    <OpenBlueInspector/>
    <div className="fg-title"><span>03 / REVIEW ON YOUR OWN COMPUTER</span><h2>Signed human acknowledgement.</h2></div>
    <section className="fg-cli"><p>Use the existing encrypted R8 Ed25519 key to acknowledge a specific review proposal locally. The recipient will still receive nothing automatically. Verification needs an independently selected trusted public key.</p>
      {COMMANDS.map((cmd,i)=><div key={i} className="fg-command"><span>{String(i+1).padStart(2,'0')}</span><code>{cmd}</code><button onClick={()=>copy(cmd)}>Copy</button></div>)}
      <div className="fg-warning">Signed acknowledgement confirms control of the selected key over the proposal bytes. It does not prove the target received the artifact, prevent replay, confirm human identity, or authorize any job. An enforcing, time/budget-scoped one-time grant is future work.</div>
    </section>
  </div>;
}
