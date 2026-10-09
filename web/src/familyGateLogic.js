/** Static EVIE family artifact-review envelopes. NOT transport or execution authority. */
export const PROPOSAL_SCHEMA = 'evie.family-handoff-proposal/1';
export const MAX_ARTIFACT_BYTES = 8 * 1024 * 1024;

export function createFamilyProposal({ target, artifactKind, sha256, size, createdAt, nonce, ttlMinutes = 15 }, catalog) {
  const entry = catalog?.targets?.find(t => t.id === target);
  if (!entry || !entry.artifactKinds.includes(artifactKind)) throw Error('Unsupported recipient/artifact combination.');
  if (typeof sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(sha256)) throw Error('Invalid artifact SHA-256.');
  if (!Number.isInteger(size) || size < 1 || size > MAX_ARTIFACT_BYTES) throw Error('Artifact must be 1 byte to 8 MB.');
  if (!Number.isInteger(ttlMinutes) || ttlMinutes < 1 || ttlMinutes > 30) throw Error('TTL must be 1–30 minutes.');
  if (typeof nonce !== 'string' || !/^[a-f0-9]{32}$/.test(nonce)) throw Error('Invalid nonce.');
  const now = new Date(createdAt);
  if (!(now instanceof Date) || !Number.isFinite(now.getTime()) || typeof createdAt !== 'string' || !createdAt.endsWith('Z')) {
    throw Error('Timestamp must be UTC.');
  }
  return {
    schemaVersion: PROPOSAL_SCHEMA, source: 'EVIE',
    target, artifactKind, artifactSha256: sha256,
    artifactBytes: size, intent: 'manual_inspection_only',
    nonce, createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + ttlMinutes * 60_000).toISOString(),
    requestedEffects: [], executionAuthorized: false, transportEnabled: false,
  };
}

export async function reviewLocalArtifact(file, target, catalog, cryptoProvider = globalThis.crypto) {
  if (!file || !Number.isInteger(file.size) || file.size < 1 || file.size > MAX_ARTIFACT_BYTES) {
    throw Error('Choose a local artifact under 8 MB.');
  }
  if (!cryptoProvider?.subtle || typeof cryptoProvider.randomUUID !== 'function') {
    throw Error('Secure browser crypto unavailable.');
  }
  const entry = catalog.targets.find(t => t.id === target);
  if (!entry) throw Error('Unknown destination.');
  const bytes = await file.arrayBuffer();
  const hash = await cryptoProvider.subtle.digest('SHA-256', bytes);
  const digest = [...new Uint8Array(hash)].map(x => x.toString(16).padStart(2, '0')).join('');
  return createFamilyProposal({
    target, artifactKind: entry.artifactKinds[0], sha256: digest, size: bytes.byteLength,
    nonce: cryptoProvider.randomUUID().replaceAll('-', ''), createdAt: new Date().toISOString(),
  }, catalog);
}

export function exportProposal(proposal) {
  const blob = new Blob([JSON.stringify(proposal, null, 2) + '\n'], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = 'evie-family-review.proposal.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally { setTimeout(() => URL.revokeObjectURL(url), 0); }
}
