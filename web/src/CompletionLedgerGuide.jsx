import {useState} from 'react';
import './completionLedgerGuide.css';

const COMMANDS = [
  {label:'Audit the known execution lanes',command:'python -m tools.evie_completion_audit entrypoints',
    summary:'Read-only inventory of six known CLI entrypoints, their source SHA-256 and whether each requires a signed lease or Docker. Not a full repository security scan.'},
  {label:'Inspect a local paused or completed session',command:'python -m tools.evie_completion_audit session --session-dir ../evie-flow-session-001',
    summary:'Checks the actual local artifacts and events. A staged distribution draft is NOT fully approved or independently verified without trust evidence.'},
  {label:'Verify the narrow draft completion contract',command:'python -m tools.evie_completion_audit session --session-dir ../evie-flow-session-001 --lease-file ../evie-flow-lease-001.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite',
    summary:'Additionally checks the Ed25519 signature, recorded attempt time, exact artifact/source/destination and spent nonce in the selected local ledger without modifying anything.'},
];
const LEVELS=[
  {state:'WAITING_FOR_REVIEW',tag:'PAUSED',info:'Nine hook artifacts staged; human approval and Stage 2 remain outstanding.'},
  {state:'ATTEMPT_OUTCOME_UNKNOWN',tag:'UNKNOWN',info:'A resume attempt was recorded, but no completed-stage event exists. No retry or DONE claim.'},
  {state:'DRAFT_STAGED_APPROVAL_UNVERIFIED',tag:'REVIEW',info:'Downstream bytes match the local receipts, but independent signing and ledger evidence were not supplied.'},
  {state:'LOCAL_DRAFT_CONTRACT_VERIFIED',tag:'BOUNDED',info:'Local draft hashes and the chosen signer/ledger match. The limited draft handoff qualifies, NOT final release.'},
];
export default function CompletionLedgerGuide(){
 const [copied,setCopied]=useState('');
 const copy=async(command)=>{
   try{await navigator.clipboard.writeText(command);setCopied('Copied. This audit reads local evidence and writes no report files.');}
   catch{setCopied('Clipboard unavailable; select the command text to copy manually.');}
 };
 return <section className="clg-root">
   <div className="mc-overline">R20 / ANTI-M STYLE COMPLETION EVIDENCE / NO FALSE DONE</div>
   <header><h3>Completion Ledger Audit</h3><p>Separate a tested workflow, a signed one-use action, a locally staged artifact, and a real final release. They are four different claims, regardless of how enthusiastically software congratulates itself.</p></header>
   <div className="clg-policies"><span>READ-ONLY</span><span>EXACT BYTES + SOURCE</span><span>SIGNATURE + LOCAL NONCE</span><span>NO PUBLICATION GRANT</span></div>
   <div className="clg-command-list">{COMMANDS.map((item,i)=><article key={item.label}>
     <div className="clg-head"><span>{String(i+1).padStart(2,'0')}</span><strong>{item.label}</strong></div>
     <p>{item.summary}</p><code>{item.command}</code>
     <button onClick={()=>copy(item.command)}>Copy command</button>
   </article>)}</div>
   <div className="mc-overline">COMPLETION CONTRACT STATES</div>
   <div className="clg-states">{LEVELS.map(x=><div key={x.state}>
      <small>{x.tag}</small><strong>{x.state.replaceAll('_',' ')}</strong><p>{x.info}</p>
   </div>)}</div>
   <p className="clg-note"><strong>Boundaries:</strong> All stage-event receipts remain unsigned local observations, and a trusted key proves key possession, not real-world identity. The spent-nonce check is meaningful only for one protected SQLite ledger. A valid draft still needs independent editorial review before distribution. The original R14/R15/R16 host-side paths remain callable, so no universal isolation guarantee is claimed.</p>
   {copied&&<p className="clg-status" role="status">{copied}</p>}
 </section>;
}
