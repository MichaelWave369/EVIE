import {useState} from 'react';
import './signedLeaseGuide.css';

const SETUP='python -m tools.evie_attest keygen --private ../evie-lease-private.pem --public ../evie-lease-trusted-public.pem';
const ISSUE='python -m tools.evie_action_lease issue --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --signing-key ../evie-lease-private.pem --lease-file ../review.lease.json';
const CHECK='python -m tools.evie_action_lease verify --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --lease-file ../review.lease.json --trusted-public ../evie-lease-trusted-public.pem';
const RUN='python -m tools.evie_approved_distribution --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --lease-file ../review.lease.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution';
const tasks=[
 {title:'Create the local signing keys (once)',command:SETUP,hint:'Use a strong passphrase. Keep your encrypted private key private and select your trusted public key independently.'},
 {title:'Sign a short-lived lease (for this artifact)',command:ISSUE,hint:'Review the unchanged R14 hooks first. Replace YOUR_REVIEWED_64_CHARACTER_SHA256 with the exact artifact digest.'},
 {title:'Inspect the signature before running',command:CHECK,hint:'Signature verification does not consume the lease or check a previous spend in the local ledger.'},
 {title:'Spend once and stage the local draft',command:RUN,hint:'The first valid attempt burns the nonce in the stable SQLite ledger, even if generation later fails. Keep using the same ledger.'},
];
export default function SignedLeaseGuide(){
 const [notice,setNotice]=useState('');
 const copy=async(command)=>{
   try{await navigator.clipboard.writeText(command);setNotice('Command copied. Replace the digest placeholder and confirm the local paths.');}
   catch{setNotice('Clipboard unavailable; select the visible command manually.');}
 };
 return <section className="slg-root">
   <div className="mc-overline">R16 / OPTIONAL SIGNED LOCAL APPROVAL PATH</div>
   <div className="slg-head">
     <div><h3>Single-use action leases</h3>
       <p>Require an independently trusted Ed25519 signing key, exact hook artifact, one destination, a short expiry and a bounded runtime before invoking R15's actual local distribution producer.</p>
     </div>
     <span>SIGNED · EXPIRES · ONE USE PER LEDGER</span>
   </div>
   <div className="slg-warning">
     <strong>Two honest lanes.</strong> R15's original operator-confirmed SHA command still exists for compatibility. This stronger R16 command checks a signed lease and burns its nonce in one local ledger before the second producer starts. It does not prohibit directly running legacy local code, authenticate a real-world person or create an OS sandbox.
   </div>
   <div className="slg-steps">
     {tasks.map((item,i)=><div className="slg-step" key={item.title}>
       <div className="slg-step-header"><b>{String(i+1).padStart(2,'0')}</b><strong>{item.title}</strong></div>
       <p>{item.hint}</p><code>{item.command}</code>
       <button onClick={()=>copy(item.command)}>Copy command</button>
     </div>)}
   </div>
   <p className="slg-boundary">Default lease: five minutes, one attempted second-stage run, twenty-second maximum, 32 KB distribution artifact. **A failed attempt still consumes the lease.** Run keys and ledger outside the Git checkout. Never publish the private key, receipts or content files. This is local-only, not a network service or a verified identity system.</p>
   {notice&&<p role="status" className="slg-notice">{notice}</p>}
 </section>;
}
