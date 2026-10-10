import {useState} from 'react';
import './safeEntryGuide.css';

const ROOT='python -m tools.evie_safe';
const COMMANDS=[
  {label:'Read migration policy',command:ROOT+' policy',
    note:'Read-only inventory of known old host-execution lanes. Nothing is shut off or executed.'},
  {label:'Preview the governed flow',command:ROOT+' plan',
    note:'Read the exact two-stage source-only plan before running any module.'},
  {label:'Start one isolated hooks session',command:ROOT+' start --session-dir ../evie-flow-session-001 --script-file ./draft.txt --topic "EVIE Creator Loop" --confirm-local-execution',
    note:'Real HooksGenerator in offline Docker, then a hard stop for human review.'},
  {label:'Inspect progress without executing',command:ROOT+' status --session-dir ../evie-flow-session-001',
    note:'Checks local evidence; no signing, Docker invocation, retry, or file creation.'},
  {label:'Resume only with your separate signed lease',command:ROOT+' resume --session-dir ../evie-flow-session-001 --lease-file ../evie-flow-lease-001.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution',
    note:'Requires a separate, previously issued Ed25519 lease for the exact input and destination. One attempted offline Docker draft; no publishing.'},
  {label:'Audit narrow draft completion',command:ROOT+' audit --session-dir ../evie-flow-session-001 --lease-file ../evie-flow-lease-001.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite',
    note:'Read-only comparison of actual artifacts, signature and local spent-nonce ledger. Never marks final DONE.'},
];
export default function SafeEntryGuide(){
  const [notice,setNotice]=useState('');
  const copy=async command=>{
    try{await navigator.clipboard.writeText(command);setNotice('Command copied. Verify local paths, permissions and signed lease scope before running.');}
    catch{setNotice('Clipboard unavailable; select the command manually.');}
  };
  return <section className="seg-root">
    <div className="mc-overline">R21 / RECOMMENDED DEFAULT · ALLOWLIST ONLY</div>
    <header><h3>EVIE Safe Entry</h3>
      <p>One predictable local command family, built on the real governed controller. It offers only source inspection, isolated hooks, read-only status, independently signed Docker resume and completion auditing.</p>
    </header>
    <div className="seg-flags"><span>NO ARBITRARY MODULES</span><span>NO HOST FALLBACK</span><span>NO AUTO SIGNING</span><span>NO PUBLISHING</span></div>
    <div className="seg-steps">
      {COMMANDS.map((step,i)=><article key={step.label}>
        <div className="seg-title"><small>{String(i+1).padStart(2,'0')}</small><strong>{step.label}</strong></div>
        <p>{step.note}</p><code>{step.command}</code>
        <button onClick={()=>copy(step.command)}>Copy local command</button>
      </article>)}
    </div>
    <p className="seg-boundary">Before the signed <code>resume</code>, review <code>hooks/nine-hooks.json</code> and issue the short-lived approval yourself with <code>python -m tools.evie_action_lease issue</code>. Docker and the local runtime image are required for either governed execution stage. The older standalone R13–R17 commands still exist and can be invoked directly; this new default launcher cannot revoke local host permissions or enforce policy over other entrypoints. Completed draft evidence is not publication or final DONE.</p>
    {notice&&<p className="seg-feedback" role="status">{notice}</p>}
  </section>;
}
