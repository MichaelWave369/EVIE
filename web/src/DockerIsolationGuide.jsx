import {useState} from 'react';
import './dockerIsolationGuide.css';

const IMAGE='docker pull python:3.11-slim';
const RUN='python -m tools.evie_isolated_distribution --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --lease-file ../review.lease.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution';

export default function DockerIsolationGuide(){
  const [message,setMessage]=useState('');
  const copy=async content=>{
    try{await navigator.clipboard.writeText(content);setMessage('Command copied. Keep your reviewed digest and folder names consistent with the signed lease.');}
    catch{setMessage('Clipboard unavailable; select and copy the command.');}
  };
  return <section className="dix-root">
    <div className="mc-overline">R17 / OPTIONAL HARDER EXECUTION BOUNDARY</div>
    <header><h3>Offline Docker capsule</h3>
      <p>Execute the R16 signed, single-use distribution-draft attempt inside a minimal source capsule with no external network, read-only container root, reduced capabilities, an unprivileged user, and explicit memory/CPU/PID caps.</p>
    </header>
    <div className="dix-badges"><span>NO HOST REPO MOUNT</span><span>NO NETWORK EGRESS</span><span>32 KB OUTPUT</span><span>NO PYTHON FALLBACK</span></div>
    <div className="dix-steps">
      <div><strong>01 · Prepare your own Docker Desktop installation</strong>
        <p>This optional lane requires a trusted running Docker daemon and the explicitly preinstalled Python image. Installing Docker or pulling a container image is a separate choice you make.</p>
        <div className="dix-command"><code>{IMAGE}</code><button onClick={()=>copy(IMAGE)}>Copy image command</button></div>
      </div>
      <div><strong>02 · Use your existing signed R16 lease</strong>
        <p>First generate nine hooks, review their SHA-256, create an Ed25519 lease for the exact new stage folder, and keep the same ledger. Then use this **isolated** runner instead of the older R16 runner.</p>
        <div className="dix-command"><code>{RUN}</code><button onClick={()=>copy(RUN)}>Copy isolated command</button></div>
      </div>
    </div>
    <p className="dix-note"><strong>Important:</strong> Missing Docker, an unavailable local image, invalid signed approval, or failure of the isolated container means **no fallback** to the unrestricted host subprocess. If the signed lease has already been spent, even a failed container run requires a fresh review destination and lease. This optional command isolates the second distribution step. In R19's governed controller, the first hooks step is also isolated. The older standalone R14 command remains a host subprocess. Docker itself is not a guarantee against a compromised host, daemon, or kernel.</p>
    {message&&<p className="dix-message" role="status">{message}</p>}
  </section>;
}
