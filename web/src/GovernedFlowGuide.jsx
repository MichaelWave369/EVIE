import {useState} from 'react';
import './governedFlowGuide.css';

const COMMANDS=[
  {
    label:'01 / Preflight the exact two-step source',
    command:'python -m tools.evie_governed_flow plan',
    note:'Reads the registered two-module plan; runs nothing and writes nothing.',
  },
  {
    label:'02 / Start: produce nine local hooks and STOP',
    command:'python -m tools.evie_governed_flow start --session-dir ../evie-flow-session-001 --script-file ./draft.txt --topic "EVIE Creator Loop" --confirm-local-execution',
    note:'Runs the existing R14 generator on the host, creates the session once, and stages a paused event. No Docker, signing, distribution or publishing.',
  },
  {
    label:'03 / Review the source hooks and check status',
    command:'python -m tools.evie_governed_flow status --session-dir ../evie-flow-session-001',
    note:'Read hooks/nine-hooks.json and its SHA-256. The status command never executes a worker. If the draft is unacceptable, start a NEW session with improved input.',
  },
  {
    label:'04 / Sign a short-lived lease for this paused session',
    command:'python -m tools.evie_action_lease issue --hooks-dir ../evie-flow-session-001/hooks --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-flow-session-001/distribution --signing-key ../evie-lease-private.pem --lease-file ../evie-flow-lease-001.json',
    note:'This is a separate conscious approval, requiring the encrypted private key passphrase. The signed action grants ONE local distribution-draft attempt, not publishing.',
  },
  {
    label:'05 / Resume ONCE using signed offline Docker',
    command:'python -m tools.evie_governed_flow resume --session-dir ../evie-flow-session-001 --lease-file ../evie-flow-lease-001.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution',
    note:'No direct host-Python fallback. Requires a fresh signature, intact single-host nonce ledger and installed Docker image. Writes attempt event before execution.',
  },
];
export default function GovernedFlowGuide(){
  const [notice,setNotice]=useState('');
  const copy=async(command)=>{
    try { await navigator.clipboard.writeText(command);
      setNotice('Command copied. Replace paths and the exact digest before running.'); }
    catch {setNotice('Clipboard unavailable; select and copy the command manually.');}
  };
  return <section className="gfg-root">
    <div className="mc-overline">R18 / REAL TWO-STAGE WORKFLOW CONTROLLER</div>
    <header>
      <h3>Governed Flow Console</h3>
      <p>One controlled local session. EVIE generates genuine hooks, pauses for inspection, then accepts a separately signed, single-use approval to draft distribution content inside the R17 Docker capsule.</p>
    </header>
    <div className="gfg-states" aria-label="Governed workflow states">
      <span>HOOKS STAGED</span><b>→</b><span>HUMAN REVIEW PAUSE</span><b>→</b><span>SIGNED DOCKER ATTEMPT</span><b>→</b><span>LOCAL DRAFT REVIEW</span>
    </div>
    <p className="gfg-warning">Every transition is operator-directed. The public web app cannot run local Python, sign leases, launch Docker, or publish content. If Stage 2 fails after the attempt event, this session does NOT auto-retry. A draft is not an approved release.</p>
    <div className="gfg-commands">{COMMANDS.map(item=><article className="gfg-command" key={item.label}>
      <strong>{item.label}</strong>
      <p>{item.note}</p>
      <code>{item.command}</code>
      <button onClick={()=>copy(item.command)}>Copy local command</button>
    </article>)}</div>
    <p className="gfg-foot">Generated session events: <code>01-hooks-paused.json</code>, <code>02-signed-resume-attempt.json</code>, <code>03-distribution-staged.json</code>. They are create-exclusive, local, unsigned observations. The actual R16 signed lease and one-host SQLite nonce ledger supply the narrower execution authorization; the event files do not.</p>
    {notice&&<p role="status" className="gfg-notice">{notice}</p>}
  </section>;
}
