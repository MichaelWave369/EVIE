/** Browser-only inspection of an UNSIGNED local OpenBlue parser replay report.
 * Never attests origin, recipient receipt, approval, or safe execution.
 */
export const REPLAY_SCHEMA = 'evie.openblue-parser-replay/1';
const DIGEST = /^[0-9a-f]{64}$/;
const REVISION = /^[0-9a-f]{40}$/;
const NONCE = /^[0-9a-f]{32}$/;

export function checkReplayReport(raw, preflight) {
  if (typeof raw !== 'string' || new TextEncoder().encode(raw).length > 32_000)
    throw Error('Parser replay receipt must be JSON under 32 KB.');
  let report;
  try { report = JSON.parse(raw); }
  catch { throw Error('Invalid parser replay JSON.'); }
  if (!report || Array.isArray(report) || report.schemaVersion !== REPLAY_SCHEMA ||
      report.status !== 'parser_replay_pass')
    throw Error('Unsupported parser-replay result.');
  if (!preflight || preflight.result !== 'preflight_pass')
    throw Error('First preflight the actual blueprint and family review pair.');
  if (!DIGEST.test(report.artifactSha256) || !NONCE.test(report.proposalNonce) ||
      report.artifactSha256 !== preflight.artifactSha256 ||
      report.proposalNonce !== preflight.envelopeNonce)
    throw Error('Parser replay does not match the locally inspected artifact and review nonce.');
  if (!REVISION.test(report.operatorSelectedRevision) ||
      !DIGEST.test(report.parserSha256) || !DIGEST.test(report.modelSha256))
    throw Error('OpenBlue checkout revision or source digests missing.');
  if (!Number.isInteger(report.walls) || !Number.isInteger(report.symbols) ||
      report.walls !== preflight.walls || report.symbols !== preflight.symbols ||
      report.units !== preflight.units)
    throw Error('Parser replay geometry differs from local preflight.');
  if (typeof report.reviewedAt !== 'string' || !Number.isFinite(Date.parse(report.reviewedAt)))
    throw Error('Parser replay timestamp malformed.');
  if (report.localParserExecuted !== true || report.preflightPassed !== true ||
      report.recipientAppAccepted !== false || report.projectImported !== false ||
      report.humanApprovalGranted !== false || report.transportEnabled !== false ||
      report.actionAuthorized !== false || report.signed !== false ||
      report.authenticatedRecipient !== false || report.proofScope !== 'operator-run-local-source-replay-only')
    throw Error('Parser replay has an unsupported claim of approval or authority.');
  return {
    match: true, status: 'matching_unsigned_parser_replay',
    artifactSha256: report.artifactSha256,
    operatorSelectedRevision: report.operatorSelectedRevision,
    parserSha256: report.parserSha256,
    modelSha256: report.modelSha256,
    walls: report.walls, symbols: report.symbols,
    imported: false, approved: false, authenticated: false,
    explanation: 'File fields match the local preflight. This unsigned report is self-reported and not independently authenticated.',
  };
}
