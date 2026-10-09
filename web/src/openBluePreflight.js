/** R9: strict-ish, read-only OpenBlue file preflight. No transport or project mutation.
 * The actual OpenBlue importer remains authoritative and still requires human approval.
 */
import { PROPOSAL_SCHEMA, MAX_ARTIFACT_BYTES } from './familyGateLogic.js';

export const OPENBLUE_SCHEMA = 'openblueprint.evie-proposal/1';
export const OPENBLUE_MAX_BYTES = 5_000_000;
export const OPENBLUE_MAX_ELEMENTS = 400;
const ID_TEXT = value => typeof value === 'string' && value.length <= 120
  && !/[\u0000-\u001f\u007f]/.test(value);
const label = value => ID_TEXT(value) && !!value.trim();
const number = (value, low, high) => typeof value === 'number' && Number.isFinite(value)
  && value >= low && value <= high;
const hex = bytes => Array.from(new Uint8Array(bytes)).map(x => x.toString(16).padStart(2,'0')).join('');
const SYMBOLS = new Set(['door', 'window', 'outlet', 'network']);
const PROPOSAL_KEYS = ['schemaVersion','source','target','artifactKind','artifactSha256',
  'artifactBytes','intent','nonce','createdAt','expiresAt','requestedEffects',
  'executionAuthorized','transportEnabled'];

function invalid(message) { throw Error(message); }
function inspectGeometry(value) {
  if (!value || Array.isArray(value) || typeof value !== 'object' || value.schemaVersion !== OPENBLUE_SCHEMA)
    invalid('Unsupported OpenBlue proposal schema.');
  const source = value.source;
  if (!source || Array.isArray(source) || source.system !== 'EVIE' || !label(source.cardId)
    || !label(source.runId) || !['fixture','generated'].includes(source.mode))
    invalid('OpenBlue source declaration invalid.');
  const p = value.project;
  if (!p || Array.isArray(p) || p.schemaVersion !== 'openblueprint.project/1')
    invalid('Unsupported nested project schema.');
  const meta = p.metadata;
  if (!meta || typeof meta !== 'object' || Array.isArray(meta) ||
    typeof meta.title !== 'string' || meta.title.length > 160 ||
    !['ft','m'].includes(meta.units) || !number(meta.grid, .01, 100))
    invalid('Invalid project metadata, units or grid.');
  if (typeof meta.updatedAt !== 'undefined' && typeof meta.updatedAt !== 'string')
    invalid('Invalid project update timestamp.');
  if (!Array.isArray(p.walls) || !Array.isArray(p.symbols) ||
    p.walls.length + p.symbols.length > OPENBLUE_MAX_ELEMENTS)
    invalid('OpenBlue review element limit is 400.');
  const seen = new Set();
  for (const [index, w] of p.walls.entries()) {
    if (!w || typeof w !== 'object' || Array.isArray(w) || !ID_TEXT(w.id) || seen.has(w.id))
      invalid('Invalid or duplicate wall ID.');
    seen.add(w.id);
    if (!['x1','y1','x2','y2'].every(k => number(w[k], -10000, 10000)) ||
      !number(w.thickness, .1, 10) || !number(w.height, .5, 100) ||
      Math.hypot(w.x2-w.x1, w.y2-w.y1) < .1)
      invalid('Wall '+index+' geometry is invalid.');
  }
  for (const [index, s] of p.symbols.entries()) {
    if (!s || typeof s !== 'object' || Array.isArray(s) || !ID_TEXT(s.id) ||
      seen.has(s.id) || !SYMBOLS.has(s.type) || !number(s.x,-10000,10000) ||
      !number(s.y,-10000,10000) ||
      !number(s.rotation ?? 0, -36000, 36000))
      invalid('Invalid symbol '+index+' geometry or duplicate ID.');
    seen.add(s.id);
  }
  return { units: meta.units, walls: p.walls.length, symbols: p.symbols.length, sourceMode: source.mode };
}

function checkEnvelope(envelope, size, date) {
  if (!envelope || typeof envelope !== 'object' || Array.isArray(envelope) ||
    Object.keys(envelope).length !== PROPOSAL_KEYS.length ||
    !PROPOSAL_KEYS.every(k => Object.hasOwn(envelope, k)) ||
    envelope.schemaVersion !== PROPOSAL_SCHEMA || envelope.source !== 'EVIE')
    invalid('Malformed family handoff review envelope.');
  if (envelope.target !== 'openblue' || envelope.artifactKind !== OPENBLUE_SCHEMA)
    invalid('Review envelope is not for OpenBlue.');
  if (!/^[a-f0-9]{64}$/.test(envelope.artifactSha256) ||
    !Number.isInteger(envelope.artifactBytes) || envelope.artifactBytes !== size)
    invalid('Artifact byte length or SHA-256 declaration invalid.');
  if (envelope.intent !== 'manual_inspection_only' ||
      envelope.executionAuthorized !== false || envelope.transportEnabled !== false ||
      !Array.isArray(envelope.requestedEffects) || envelope.requestedEffects.length !== 0)
    invalid('Handoff may not request execution or transport.');
  if (typeof envelope.nonce !== 'string' || !/^[a-f0-9]{32}$/.test(envelope.nonce))
    invalid('Invalid envelope nonce.');
  if (typeof envelope.createdAt !== 'string' || typeof envelope.expiresAt !== 'string' ||
      !envelope.createdAt.endsWith('Z') || !envelope.expiresAt.endsWith('Z'))
    invalid('Review envelope timestamps must be UTC.');
  const created = Date.parse(envelope.createdAt), expires = Date.parse(envelope.expiresAt);
  const clock = date instanceof Date ? date.getTime() : Number(date);
  if (!Number.isFinite(created) || !Number.isFinite(expires) || !Number.isFinite(clock) ||
      expires <= created || expires-created > 30*60*1000 ||
      created > clock + 2*60*1000 || expires < clock - 2*60*1000)
    invalid('Envelope expired or timestamp bounds invalid.');
}

export async function inspectOpenBlueHandoff(envelope, artifactBytes, cryptoProvider = globalThis.crypto, now = new Date()) {
  const bytes = artifactBytes instanceof ArrayBuffer ? new Uint8Array(artifactBytes) : artifactBytes;
  if (!(bytes instanceof Uint8Array) || !bytes.length ||
      bytes.byteLength > Math.min(OPENBLUE_MAX_BYTES, MAX_ARTIFACT_BYTES))
    invalid('OpenBlue artifact must be under 5 MB.');
  checkEnvelope(envelope, bytes.byteLength, now);
  if (!cryptoProvider?.subtle) invalid('Secure SHA-256 browser hashing unavailable.');
  const digest = hex(await cryptoProvider.subtle.digest('SHA-256', bytes));
  if (digest !== envelope.artifactSha256) invalid('Artifact SHA-256 mismatch: file was changed.');
  let raw;
  try { raw = JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(bytes)); }
  catch { invalid('Invalid UTF-8 JSON blueprint.'); }
  const geometry = inspectGeometry(raw);
  return {
    schemaVersion: 'evie.openblue-preflight/1',
    result: 'preflight_pass',
    artifactSha256: digest,
    artifactBytes: bytes.byteLength,
    target: 'openblue',
    envelopeNonce: envelope.nonce,
    expiresAt: envelope.expiresAt,
    ...geometry,
    digestMatch: true, schemaMatch: true,
    recipientAccepted: false, executionAuthorized: false,
    transportEnabled: false, authenticated: false,
    note: 'This browser preflight is not a live OpenBlue import or an authenticated acknowledgement.',
  };
}

export async function inspectLocalOpenBlueFiles(envelopeFile, artifactFile) {
  if (!envelopeFile || envelopeFile.size > 32_000 || !artifactFile ||
      artifactFile.size > OPENBLUE_MAX_BYTES)
    invalid('Choose a review JSON under 32 KB and an OpenBlue proposal JSON under 5 MB.');
  let review;
  try { review = JSON.parse(await envelopeFile.text()); }
  catch { invalid('Invalid family review JSON.'); }
  return inspectOpenBlueHandoff(review, await artifactFile.arrayBuffer());
}
