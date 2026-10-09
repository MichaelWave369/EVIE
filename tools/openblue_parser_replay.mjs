/** EVIE R10: read-only conformance replay through a locally selected OpenBlue parser.
 *
 * Runs JS from the selected checkout. ONLY use a source revision you trust.
 * No API transport, browser opening, project save, import approval or authorization.
 */
import { createHash, webcrypto } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, lstatSync, readFileSync, openSync, closeSync, writeFileSync, unlinkSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { inspectOpenBlueHandoff } from '../web/src/openBluePreflight.js';

export const REPLAY_SCHEMA = 'evie.openblue-parser-replay/1';
const MAX_ARTIFACT = 5_000_000;
const MAX_REVIEW = 32_000;
const REVISION = /^[a-f0-9]{40}$/;
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

function trustedFile(path, maxBytes) {
  const file = resolve(path);
  const info = lstatSync(file);
  if (!info.isFile() || info.isSymbolicLink() || !info.size || info.size > maxBytes)
    throw Error('selected local file must be a non-symlink regular file within size limits');
  return readFileSync(file);
}
function git(dir, ...args) {
  return execFileSync('git', ['-C', dir, ...args], {
    encoding: 'utf8', timeout: 5_000, maxBuffer: 32_000,
    stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true,
  }).trim();
}
function cleanOpenBlueSource(root, expectedRevision) {
  if (typeof expectedRevision !== 'string' || !REVISION.test(expectedRevision))
    throw Error('explicit 40-character expected OpenBlue git revision is required');
  const directory = resolve(root);
  const head = git(directory, 'rev-parse', 'HEAD');
  if (head !== expectedRevision) throw Error('OpenBlue checkout revision does not match operator-selected pin');
  const top = resolve(git(directory, 'rev-parse', '--show-toplevel'));
  if (top !== directory) throw Error('select the OpenBlue repository root');
  const files = ['package.json', 'src/evieBridge.js', 'src/model.js'];
  for (const path of files) {
    const file = join(directory, path);
    if (!existsSync(file) || lstatSync(file).isSymbolicLink() || !lstatSync(file).isFile())
      throw Error('missing or symlinked OpenBlue parser source file');
  }
  const dirt = git(directory, 'status', '--porcelain', '--untracked-files=normal', '--',
    ...files);
  if (dirt) throw Error('OpenBlue parser/source files differ from selected git commit');
  const pkg = JSON.parse(readFileSync(join(directory, 'package.json'), 'utf8'));
  if (pkg.name !== 'openblue' || pkg.type !== 'module')
    throw Error('selected project is not the audited OpenBlue ESM checkout');
  return { directory, head,
    parserHash: digest(readFileSync(join(directory, 'src/evieBridge.js'))),
    modelHash: digest(readFileSync(join(directory, 'src/model.js'))) };
}

export async function replayOpenBlue({
  openblueDir, expectedRevision, envelope, artifactBytes,
  now = new Date(),
}) {
  // Validation first: never import external JS if the envelope is stale or tampered.
  const preflight = await inspectOpenBlueHandoff(envelope, artifactBytes, webcrypto, now);
  const source = cleanOpenBlueSource(openblueDir, expectedRevision);
  // This explicitly runs trusted local OpenBlue source in the current Node process.
  // Git revision pinning prevents accidental drift; it is NOT a malicious-code sandbox.
  const { parseEvieProposal } = await import(pathToFileURL(join(source.directory, 'src/evieBridge.js')).href);
  if (typeof parseEvieProposal !== 'function') throw Error('OpenBlue parser export not found');
  const bytes = Buffer.from(artifactBytes);
  const parsed = parseEvieProposal(new TextDecoder('utf-8', {fatal:true}).decode(bytes));
  if (parsed?.schemaVersion !== 'openblueprint.evie-proposal/1' ||
      parsed?.project?.schemaVersion !== 'openblueprint.project/1' ||
      parsed.source?.system !== 'EVIE' ||
      parsed.project.walls.length !== preflight.walls ||
      parsed.project.symbols.length !== preflight.symbols ||
      parsed.project.metadata.units !== preflight.units) {
    throw Error('OpenBlue parser output diverges from EVIE preflight');
  }
  return {
    schemaVersion: REPLAY_SCHEMA,
    status: 'parser_replay_pass',
    operatorSelectedRevision: source.head,
    parserSha256: source.parserHash,
    modelSha256: source.modelHash,
    artifactSha256: digest(bytes),
    proposalNonce: envelope.nonce,
    artifactKind: envelope.artifactKind,
    reviewedAt: new Date().toISOString(),
    walls: parsed.project.walls.length,
    symbols: parsed.project.symbols.length,
    units: parsed.project.metadata.units,
    localParserExecuted: true,
    preflightPassed: true,
    recipientAppAccepted: false,
    projectImported: false,
    humanApprovalGranted: false,
    transportEnabled: false,
    actionAuthorized: false,
    signed: false,
    authenticatedRecipient: false,
    proofScope: 'operator-run-local-source-replay-only',
    note: 'OpenBlue parser was invoked in this local Node process, not in the running OpenBlue app. Unsigned and not recipient-issued.',
  };
}

export function writeReplayReceipt(path, record) {
  const destination = resolve(path);
  if (!existsSync(dirname(destination))) throw Error('receipt directory must exist');
  const serialized = Buffer.from(JSON.stringify(record, null, 2) + '\n');
  if (serialized.length > 32_000) throw Error('receipt exceeds output limit');
  const fd = openSync(destination, 'wx', 0o600);
  try { writeFileSync(fd, serialized); }
  catch (e) { closeSync(fd); unlinkSync(destination); throw e; }
  closeSync(fd);
}

function cliOptions() {
  const { values } = parseArgs({
    options: {
      'openblue-dir': { type: 'string' },
      'expected-revision': { type: 'string' },
      'proposal': { type: 'string' },
      'artifact': { type: 'string' },
      'receipt': { type: 'string' },
    },
    strict: true,
  });
  for (const required of ['openblue-dir', 'expected-revision', 'proposal', 'artifact']) {
    if (!values[required]) throw Error('missing --' + required);
  }
  return values;
}

async function main() {
  try {
    const flags = cliOptions();
    const proposalBytes = trustedFile(flags.proposal, MAX_REVIEW);
    const artifactBytes = trustedFile(flags.artifact, MAX_ARTIFACT);
    const envelope = JSON.parse(proposalBytes.toString('utf8'));
    const result = await replayOpenBlue({
      openblueDir: flags['openblue-dir'],
      expectedRevision: flags['expected-revision'],
      envelope, artifactBytes,
    });
    if (flags.receipt) writeReplayReceipt(flags.receipt, result);
    process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  } catch (e) {
    // Errors are intentionally code-level only. Do not echo potentially private paths.
    process.stdout.write(JSON.stringify({
      schemaVersion: REPLAY_SCHEMA, status: 'fail',
      reason: e instanceof SyntaxError ? 'invalid_json' : 'replay_rejected',
      recipientAppAccepted: false, actionAuthorized: false,
    }) + '\n');
    process.exitCode = 1;
  }
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
