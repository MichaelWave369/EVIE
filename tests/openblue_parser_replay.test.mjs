/** Cross-repo Node tests: execute OpenBlue's actual local parser, without project mutation.
 * CI explicitly checks out a pinned OpenBlue revision in a sibling workspace folder.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import { mkdtempSync, readFileSync, readdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createDemoProposal } from '../web/src/blueprint.js';
import { createFamilyProposal } from '../web/src/familyGateLogic.js';
import { replayOpenBlue, writeReplayReceipt } from '../tools/openblue_parser_replay.mjs';

const OPENBLUE_CHECKOUT = process.env.OPENBLUE_CHECKOUT;
const OPENBLUE_REVISION = process.env.OPENBLUE_REVISION;
if (process.env.CI && (!OPENBLUE_CHECKOUT || !OPENBLUE_REVISION))
  throw Error('Cross-repo CI requires explicitly pinned OpenBlue source');
const ready = Boolean(OPENBLUE_CHECKOUT && OPENBLUE_REVISION);
const catalog = {
  targets: [{ id:'openblue', artifactKinds:['openblueprint.evie-proposal/1'] }],
};
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

async function fixture() {
  const artifact = createDemoProposal({ width:24, depth:16, partition:'vertical' });
  const bytes = Buffer.from(JSON.stringify(artifact));
  const nonce = 'a'.repeat(32);
  const envelope = createFamilyProposal({
    target:'openblue', artifactKind:'openblueprint.evie-proposal/1',
    size:bytes.length, sha256:sha(bytes), createdAt:new Date().toISOString(),
    nonce, ttlMinutes:15,
  }, catalog);
  return {artifact, bytes, envelope};
}

test('actual OpenBlue parser accepts matching digest-bound EVIE fixture, but cannot approve it', {
  skip: !ready,
}, async () => {
  const data = await fixture();
  const record = await replayOpenBlue({
    openblueDir: OPENBLUE_CHECKOUT, expectedRevision: OPENBLUE_REVISION,
    envelope:data.envelope, artifactBytes:data.bytes,
  });
  assert.equal(record.status, 'parser_replay_pass');
  assert.equal(record.operatorSelectedRevision, OPENBLUE_REVISION);
  assert.equal(record.artifactSha256, sha(data.bytes));
  assert.equal(record.proposalNonce, data.envelope.nonce);
  assert.equal(record.walls, 5);
  assert.equal(record.symbols, 2);
  for (const key of ['recipientAppAccepted','projectImported','humanApprovalGranted',
                      'transportEnabled','actionAuthorized','signed','authenticatedRecipient']) {
    assert.equal(record[key], false, key);
  }
  assert.equal(record.localParserExecuted, true);
  assert.match(record.parserSha256, /^[0-9a-f]{64}$/);
  assert.match(record.modelSha256, /^[0-9a-f]{64}$/);
});

test('mutated bytes, wrong destination and expired envelope fail before recipient replay', {
  skip: !ready,
}, async () => {
  const data = await fixture();
  const expected = {
    openblueDir: OPENBLUE_CHECKOUT, expectedRevision: OPENBLUE_REVISION,
    envelope:data.envelope, artifactBytes:data.bytes,
  };
  const tampered = Buffer.from(data.bytes);
  tampered[5] ^= 1;
  await assert.rejects(replayOpenBlue({...expected, artifactBytes:tampered}), /SHA-256/);
  await assert.rejects(replayOpenBlue({...expected, envelope:{...data.envelope,target:'phios'}}),
                       /OpenBlue/);
  await assert.rejects(replayOpenBlue({...expected, now:new Date(Date.now()+60*60*1000)}),
                       /expired|timestamp/);
});

test('actual parser rejects bad plan even if operator fabricates matching digest', {
  skip: !ready,
}, async () => {
  const data = await fixture();
  data.artifact.project.walls[0].x2 = 0;
  const edited = Buffer.from(JSON.stringify(data.artifact));
  const envelope = {
    ...data.envelope, artifactSha256:sha(edited), artifactBytes:edited.length,
  };
  await assert.rejects(replayOpenBlue({
    openblueDir:OPENBLUE_CHECKOUT, expectedRevision:OPENBLUE_REVISION,
    envelope, artifactBytes:edited,
  }), /wall|geometry|short|invalid/i);
});

test('incorrect source pin denies replay, and exclusive receipt creation preserves files', {
  skip: !ready,
}, async () => {
  const data = await fixture();
  await assert.rejects(replayOpenBlue({
    openblueDir:OPENBLUE_CHECKOUT, expectedRevision:'0'.repeat(40),
    envelope:data.envelope, artifactBytes:data.bytes,
  }), /revision/);
  const temp = mkdtempSync(join(tmpdir(), 'evie-openblue-replay-'));
  try {
    const proposalFile=join(temp, 'review.json'), artifactFile=join(temp, 'plan.json'),
          receiptFile=join(temp,'parser-replay.json');
    writeFileSync(proposalFile, JSON.stringify(data.envelope));
    writeFileSync(artifactFile, data.bytes);
    const result = await replayOpenBlue({
      openblueDir:OPENBLUE_CHECKOUT, expectedRevision:OPENBLUE_REVISION,
      envelope:data.envelope, artifactBytes:data.bytes,
    });
    writeReplayReceipt(receiptFile,result);
    assert.equal(JSON.parse(readFileSync(receiptFile,'utf8')).status,'parser_replay_pass');
    assert.throws(()=>writeReplayReceipt(receiptFile,result), /EEXIST/);
    assert.deepEqual(readFileSync(artifactFile),data.bytes);
    assert.equal(readdirSync(temp).length,3);
    const printed=execFileSync(process.execPath,[
      'tools/openblue_parser_replay.mjs',
      '--openblue-dir',resolve(OPENBLUE_CHECKOUT),
      '--expected-revision',OPENBLUE_REVISION,
      '--proposal',proposalFile,
      '--artifact',artifactFile,
    ],{cwd:resolve('.'),encoding:'utf8',timeout:15_000});
    assert.equal(JSON.parse(printed).status,'parser_replay_pass');
  } finally { rmSync(temp,{recursive:true,force:true}); }
});
