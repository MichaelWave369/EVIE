/** Client-only parser: validates shape/source match, NOT the authenticity of self-reports. */
export const RECEIPT_SCHEMA = 'evie.qualification-receipt/1';
const CHECKS = [
  'versioned_proposal', 'versioned_project', 'bounded_wall_geometry',
  'symbol_types', 'unique_element_ids', 'source_labels', 'run_id_bound',
  'digest_match', 'artifact_scope',
];
const HEX = /^[0-9a-f]{64}$/;

export function examineLocalReceipt(raw, catalog) {
  if (typeof raw !== 'string' || new TextEncoder().encode(raw).length > 64_000) throw Error('Receipt too large or not text.');
  let receipt;
  try { receipt = JSON.parse(raw); } catch { throw Error('Invalid receipt JSON.'); }
  if (!receipt || Array.isArray(receipt) || typeof receipt !== 'object' || receipt.schemaVersion !== RECEIPT_SCHEMA) {
    throw Error('Unsupported qualification receipt format.');
  }
  const fixture = catalog.qualificationFixtures?.find(f => f.module === receipt.module && f.scenario === receipt.scenario);
  if (!fixture) throw Error('This capability/scenario is not in the audited public fixture catalog.');
  if (receipt.origin !== 'local-subprocess-observation' || !['pass', 'fail'].includes(receipt.status)) {
    throw Error('Invalid qualification origin/status.');
  }
  if (receipt.trust?.signed !== false || receipt.trust?.authenticatedMachine !== false ||
      receipt.effectPolicy?.externalEffectsAuthorized !== false ||
      receipt.effectPolicy?.networkSandboxEnforced !== false ||
      receipt.effectPolicy?.providerEnvironmentStripped !== true ||
      receipt.effectPolicy?.temporaryWorkspace !== true) {
    throw Error('Unexpected trust or execution-policy declaration.');
  }
  if (typeof receipt.createdAt !== 'string' || !Number.isFinite(Date.parse(receipt.createdAt)) ||
      !Number.isFinite(receipt.durationMs) || receipt.durationMs < 0) throw Error('Invalid timestamp or duration.');
  if (receipt.sourceSha256 !== fixture.sourceSha256) {
    throw Error('Receipt source does not match the version of EVIE on this Pages build.');
  }
  if (receipt.status === 'pass') {
    if (!receipt.checks || Object.keys(receipt.checks).length !== CHECKS.length ||
        !CHECKS.every(key => receipt.checks[key] === true) ||
        typeof receipt.artifactSha256 !== 'string' || !HEX.test(receipt.artifactSha256)) {
      throw Error('PASS receipt lacks required checks or artifact digest.');
    }
  }
  return {
    status: receipt.status,
    module: receipt.module,
    scenario: receipt.scenario,
    createdAt: receipt.createdAt,
    durationMs: receipt.durationMs,
    sourceMatch: true,
    checkCount: receipt.status === 'pass' ? CHECKS.length : 0,
    artifactSha256: receipt.status === 'pass' ? receipt.artifactSha256 : null,
    level: 'unsigned_local_self_report',
    authenticated: false,
    caveat: 'Matching a source hash is NOT proof that the file came from a trusted machine or actually ran.',
  };
}
