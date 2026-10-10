import {useState} from 'react';
import './executionSecurityGuide.css';

const command='python -m tools.evie_execution_security assess';
const constraints=[
  ['OS client identity','No verified operating-system principal per HTTP request'],
  ['Service privilege isolation','No OS-separated, least-privilege execution broker'],
  ['Protected approval state','Local SQLite nonce ledger is still replaceable by a host user'],
  ['Mandatory legacy enforcement','The older direct Python CLIs remain callable'],
  ['Request-to-lease binding','No atomic service-owned request/lease/worker transaction'],
  ['Independent execution receipts','Current local runtime observations are unsigned'],
];

export default function ExecutionSecurityGuide(){
  const [notice,setNotice]=useState('');
  async function copy(){
    try{await navigator.clipboard.writeText(command);setNotice('Read-only assessment command copied. It does not enable execution.');}
    catch{setNotice('Clipboard unavailable; select the command text to copy manually.');}
  }
  return <section className="esg-root">
    <div className="mc-overline">R23 / FAIL-CLOSED EXECUTION-SERVICE CONTRACT</div>
    <header><h3>Security promotion gate</h3><p>Before EVIE can ever receive an HTTP execution permission, these six separate safety requirements need real implementation and test evidence. Today every requirement remains unqualified.</p></header>
    <div className="esg-closed"><strong>EXECUTION GATE CLOSED</strong><span>NO HTTP START · NO HTTP RESUME · NO HTTP PUBLISH</span></div>
    <div className="esg-checks">{constraints.map(([title,description])=><div key={title}>
       <strong>{title}</strong><p>{description}</p>
    </div>)}</div>
    <div className="esg-command"><code>{command}</code><button onClick={copy}>Copy assessment</button></div>
    <p className="esg-warning">The localhost service now provides an authenticated, read-only <code>GET /v1/security</code> report. A bearer token isn't OS identity, a signed local action isn't a service-level authorization, and a local receipt isn't proof of a trusted runtime. This audit deliberately cannot flip the execution switch. The public site does not contact your localhost.</p>
    {notice&&<p role="status" className="esg-notice">{notice}</p>}
  </section>;
}
