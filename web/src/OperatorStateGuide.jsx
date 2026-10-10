import {useState} from 'react';
import './operatorStateGuide.css';

const COMMANDS=[
  {label:'Inspect both local files (read-only)',command:'python -m tools.evie_operator_state inspect --token-file ../evie-local-service.token --ledger-file ../evie-local-lease-ledger.sqlite'},
  {label:'Inspect only your bearer-token file',command:'python -m tools.evie_operator_state inspect --token-file ../evie-local-service.token'},
];
export default function OperatorStateGuide(){
 const [message,setMessage]=useState('');
 async function copy(code){
  try{await navigator.clipboard.writeText(code);setMessage('Read-only inspector command copied. It prints no token, SID, username or file path.');}
  catch{setMessage('Clipboard unavailable; select the command manually.');}
 }
 return <section className="osg-root">
  <div className="mc-overline">R24 / LOCAL OPERATOR & FILE-STATE OBSERVATIONS</div>
  <header><h3>Operator state inspector</h3><p>Inspect the local process and storage boundaries without opening an execution route. Only local command-line tools can perform this inspection; the public website cannot read your PC.</p></header>
  <div className="osg-grid">
    <article><strong>Windows</strong><p>Uses native security APIs to compare the running process's user SID with the file owner's SID and check whether a DACL exists. Effective ACL permissions and actual HTTP-client identity remain <b>unverified</b>.</p></article>
    <article><strong>Linux / POSIX</strong><p>Checks file owner, group/world permission bits, immediate parent directory and hardlink count. These are filesystem observations, not protection from a privileged local attacker.</p></article>
  </div>
  <div className="osg-commands">{COMMANDS.map(x=><div key={x.label}><strong>{x.label}</strong><code>{x.command}</code><button onClick={()=>copy(x.command)}>Copy command</button></div>)}</div>
  <p className="osg-warning"><strong>Execution gate remains CLOSED.</strong> The inspector does not read bearer-token contents or database rows, set ACLs, change permissions, create a ledger, launch a worker, or send data to GitHub Pages. A file owned by your account still does not prove that a request came from your account.</p>
  {message&&<p className="osg-message" role="status">{message}</p>}
 </section>;
}
