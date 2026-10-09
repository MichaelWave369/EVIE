import { useState } from 'react';
import manifest from './generated/mission-control.json';
import { verifyTrustedAttestation } from './attestationVerify.js';
import './trustedAttestation.css';

const KEY_COMMAND = 'python -m tools.evie_attest keygen --private ./evie-local.pem --public ./evie-trusted.pub.pem';
const RUN_COMMAND = 'python -m tools.evie_qualify run openblueprint_floor_plan --signing-key ./evie-local.pem --attestation ./cad-run.attestation.json';
const VERIFY_COMMAND = 'python -m tools.evie_attest verify --attestation ./cad-run.attestation.json --trusted-public ./evie-trusted.pub.pem';

export default function TrustedAttestation() {
  const [attestation, setAttestation] = useState('');
  const [publicKey, setPublicKey] = useState('');
  const [trusted, setTrusted] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  async function load(event, kind, limit, callback) {
    const file = event.target.files?.[0];
    event.target.value = '';
    setResult(null);
    setError('');
    if (!file) return;
    if (file.size > limit) { setError('File exceeds local inspection limit.'); return; }
    try { callback(await file.text()); }
    catch { setError('Could not read the selected local file.'); }
  }
  async function verify() {
    if (!attestation || !publicKey || !trusted) return;
    setLoading(true);
    setResult(null);
    setError('');
    try {
      const output = await verifyTrustedAttestation(attestation, publicKey, manifest);
      setResult(output);
      setMessage('Verified locally in this browser, using the independently selected public key.');
    } catch(e) {
      setError(e instanceof Error ? e.message : 'Unable to verify attestation.');
    } finally {
      setLoading(false);
    }
  }
  async function copy(value) {
    try { await navigator.clipboard.writeText(value); setMessage('Local command copied.'); }
    catch { setMessage('Clipboard unavailable; select the command text manually.'); }
  }
  return <section className="ta-panel">
    <div className="mc-overline">R8 / KEYED EVIDENCE / LOCAL-FIRST</div>
    <h3>Trusted-key attestation</h3>
    <p>Sign one passing local CAD qualification with an encrypted Ed25519 private key. Verify its signature using a <strong>public key obtained independently</strong>, not a key supplied inside the attestation. This checks the signer key and file integrity, not whether a test truly ran.</p>
    <div className="ta-commands">
      <div><span>1 · Create encrypted keypair (one-time)</span><code>{KEY_COMMAND}</code><button onClick={()=>copy(KEY_COMMAND)}>Copy</button></div>
      <div><span>2 · Run and sign a fresh local qualification</span><code>{RUN_COMMAND}</code><button onClick={()=>copy(RUN_COMMAND)}>Copy</button></div>
      <div><span>3 · Independently verify in Python</span><code>{VERIFY_COMMAND}</code><button onClick={()=>copy(VERIFY_COMMAND)}>Copy</button></div>
    </div>
    <div className="ta-review">
      <div className="mc-overline">BROWSER / MANUAL TWO-FILE VERIFICATION</div>
      <div className="ta-file-grid">
        <label>Signed attestation JSON
          <input type="file" accept=".json,application/json" onChange={e=>load(e,'attestation',128000,setAttestation)}/>
        </label>
        <label>Trusted Ed25519 PUBLIC KEY PEM
          <input type="file" accept=".pem,.pub,text/plain" onChange={e=>load(e,'public',16000,setPublicKey)}/>
        </label>
      </div>
      <label className="ta-ack"><input type="checkbox" checked={trusted} onChange={e=>{setTrusted(e.target.checked);setResult(null);}}/> I obtained and checked this public key through a separate trusted channel, not from the attestation file itself.</label>
      <button className="ta-verify" disabled={!attestation||!publicKey||!trusted||loading} onClick={verify}>{loading?'Verifying…':'Verify signature against selected key'}</button>
      <p className="ta-meta">Private keys never enter the browser. No file is uploaded, persisted or sent to EVIE. Unsupported browsers can use the local Python verifier instead.</p>
      {error&&<p role="alert" className="ta-error">{error}</p>}
      {message&&<p role="status" className="ta-message">{message}</p>}
      {result&&<div className="ta-result"><strong>✓ Valid Ed25519 signature for selected key</strong>
        <dl><dt>Module</dt><dd>{result.module}</dd>
          <dt>Source digest</dt><dd>Matches this EVIE build</dd>
          <dt>Signer fingerprint</dt><dd><code>{result.signerFingerprint}</code></dd>
          <dt>Signed at (claimed)</dt><dd>{result.signedAt}</dd>
          <dt>Action authorization</dt><dd>NONE</dd></dl>
        <p>A matching signature only establishes that someone possessing this key signed these reported bytes. It does not establish independent execution, machine integrity, physical-world correctness, or permission to act.</p>
      </div>}
    </div>
  </section>;
}
