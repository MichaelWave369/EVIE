/** R8: verify a local Ed25519 attestation against a separately selected trust anchor.
 * Signature validity is evidence of key possession, NOT authorization or a sandbox audit.
 */
import { examineLocalReceipt } from './receiptReview.js';

const SCHEMA = 'evie.qualification-attestation/1';
const PREFIX = 'EVIE/QUALIFICATION_ATTESTATION_V1\u0000';
const HEX = bytes => [...new Uint8Array(bytes)].map(x => x.toString(16).padStart(2, '0')).join('');

function fromBase64(value, limit) {
  if (typeof value !== 'string' || value.length > Math.ceil(limit / 3) * 4 + 8 ||
      !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value)) {
    throw Error('Invalid or oversized base64 field.');
  }
  const binary = atob(value);
  if (binary.length > limit) throw Error('Decoded field is too large.');
  return Uint8Array.from(binary, ch => ch.charCodeAt(0));
}

function pemToDer(pem) {
  if (typeof pem !== 'string' || pem.length > 16_000) throw Error('Invalid public-key file size.');
  const match = pem.trim().match(/^-----BEGIN PUBLIC KEY-----\s+([A-Za-z0-9+/\s=]+)\s+-----END PUBLIC KEY-----$/);
  if (!match) throw Error('Select an Ed25519 PUBLIC KEY PEM, obtained independently.');
  return fromBase64(match[1].replace(/\s/g, ''), 4096);
}

export async function verifyTrustedAttestation(attestationText, trustedPublicPem, catalog, cryptoProvider = globalThis.crypto) {
  if (typeof attestationText !== 'string' || new TextEncoder().encode(attestationText).length > 128_000) {
    throw Error('Attestation must be JSON under 128 KB.');
  }
  if (!cryptoProvider?.subtle) throw Error('WebCrypto unavailable; use the local Python verifier.');
  let attestation;
  try { attestation = JSON.parse(attestationText); } catch { throw Error('Attestation JSON is malformed.'); }
  if (!attestation || Array.isArray(attestation) || attestation.schemaVersion !== SCHEMA || attestation.algorithm !== 'Ed25519') {
    throw Error('Unsupported signed attestation version or algorithm.');
  }
  const keyDer = pemToDer(trustedPublicPem);
  const keyFingerprint = HEX(await cryptoProvider.subtle.digest('SHA-256', keyDer));
  if (attestation.keyFingerprint !== keyFingerprint) throw Error('Signer is not the selected trusted public key.');
  let key;
  try {
    key = await cryptoProvider.subtle.importKey('spki', keyDer, { name: 'Ed25519' }, false, ['verify']);
  } catch { throw Error('Selected public key is not a supported Ed25519 key.'); }
  const payload = fromBase64(attestation.payloadBase64, 64_000);
  const signature = fromBase64(attestation.signatureBase64, 64);
  if (signature.length !== 64) throw Error('Incorrect Ed25519 signature size.');
  const prefix = new TextEncoder().encode(PREFIX);
  const message = new Uint8Array(prefix.length + payload.length);
  message.set(prefix);
  message.set(payload, prefix.length);
  const signatureValid = await cryptoProvider.subtle.verify({ name: 'Ed25519' }, key, signature, message);
  if (!signatureValid) throw Error('Signature INVALID: the payload or signature was changed.');
  let record;
  try { record = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(payload)); }
  catch { throw Error('Signed record is not valid UTF-8 JSON.'); }
  if (!record || Array.isArray(record) || Object.keys(record).sort().join(',') !== 'receipt,signedAt' ||
      typeof record.signedAt !== 'string' || !record.signedAt.endsWith('Z') ||
      !Number.isFinite(Date.parse(record.signedAt))) throw Error('Signed record shape invalid.');
  const receipt = examineLocalReceipt(JSON.stringify(record.receipt), catalog);
  if (receipt.status !== 'pass') throw Error('Only passing, allowlisted receipts can be signed.');
  return {
    signatureValid: true,
    signerFingerprint: keyFingerprint,
    signedAt: record.signedAt,
    module: receipt.module,
    scenario: receipt.scenario,
    sourceMatch: receipt.sourceMatch,
    scope: 'operator-selected-key-signature',
    actionAuthorized: false,
    caveat: 'Signature proves control of the selected key only, not that the reported test ran or any job is approved.',
  };
}
