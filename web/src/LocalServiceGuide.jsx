import {useState} from 'react';
import './localServiceGuide.css';
import ExecutionSecurityGuide from './ExecutionSecurityGuide.jsx';
import OperatorStateGuide from './OperatorStateGuide.jsx';
const COMMANDS=[
  {label:'01 · Create private local access token',command:'python -m tools.evie_local_service token --token-file ../evie-local-service.token',description:'Create a new, non-overwritten 256-bit bearer-token file OUTSIDE your Git checkout. This does not start a service or authorize an execution.'},
  {label:'02 · Start the read-only localhost service',command:'python -m tools.evie_local_service serve --token-file ../evie-local-service.token --port 8765',description:'Binds only 127.0.0.1. Keep this terminal open; Ctrl+C stops the service. It does not start Docker or any EVIE module.'},
  {label:'03 · Probe the exact allowed GET routes',command:'python -m tools.evie_local_service probe --token-file ../evie-local-service.token --port 8765',description:'In another terminal, authenticate and inspect health, declared migration policy and the source-only governed plan. The token never needs to be pasted into a website.'},
];
export default function LocalServiceGuide(){
 const [status,setStatus]=useState('');
 const copy=async command=>{
   try { await navigator.clipboard.writeText(command);setStatus('Command copied. Check the local token-file path and only start this service on a trusted PC.'); }
   catch { setStatus('Clipboard unavailable; select and copy the command yourself.'); }
 };
 return <section className="lsg-root">
   <div className="mc-overline">R22 / LOCAL READ-ONLY CONTROL PLANE · ZERO EXECUTION ENDPOINTS</div>
   <header><h3>Local Service Preview</h3><p>A deliberately tiny Windows-friendly localhost server to test the API trust boundary before EVIE accepts remote-style execution requests. It exposes only health, source policy, workflow plan and a default-deny execution-security assessment.</p></header>
   <div className="lsg-policy"><span>127.0.0.1 ONLY</span><span>BEARER TOKEN REQUIRED</span><span>NO CORS</span><span>GET ONLY</span><span>NO WORKER EXECUTION</span></div>
   <div className="lsg-commands">{COMMANDS.map(({label,command,description})=><article key={label}>
     <strong>{label}</strong><p>{description}</p><code>{command}</code>
     <button onClick={()=>copy(command)}>Copy local command</button>
   </article>)}</div>
   <div className="lsg-routes">
     <div><code>GET /v1/health</code><span>Read-only service readiness</span></div>
     <div><code>GET /v1/policy</code><span>Known CLI migration/exposure policy</span></div>
     <div><code>GET /v1/plan</code><span>Fixed two-stage workflow plan, unexecuted</span></div>
     <div><code>GET /v1/security</code><span>Default-deny service execution-readiness contract</span></div>
     <div><code>POST /v1/start</code><span>DENIED · no such route</span></div>
     <div><code>POST /v1/resume</code><span>DENIED · no such route</span></div>
   </div>
   <ExecutionSecurityGuide/>
   <OperatorStateGuide/>
   <p className="lsg-warning"><strong>Security boundary:</strong> This token is a local bearer secret, not verified user identity or an encrypted HTTPS channel. Keep its file private, especially on shared Windows accounts; protect it using local filesystem permissions. The server rejects requests with browser Origin/Referer headers and exposes no browser-control APIs. Existing Python CLIs remain separately executable. Do not expose the port through Starlink, port forwarding, tunnels, proxy servers or remote browser tools.</p>
   {status&&<p className="lsg-feedback" role="status">{status}</p>}
 </section>;
}
