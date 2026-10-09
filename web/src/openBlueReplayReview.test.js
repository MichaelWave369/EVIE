import { describe, it, expect } from 'vitest';
import { checkReplayReport } from './openBlueReplayReview.js';

const sha='a'.repeat(64), nonce='b'.repeat(32);
const preflight={result:'preflight_pass',artifactSha256:sha,envelopeNonce:nonce,walls:5,symbols:2,units:'ft'};
const report={
  schemaVersion:'evie.openblue-parser-replay/1',status:'parser_replay_pass',
  operatorSelectedRevision:'f'.repeat(40),parserSha256:'c'.repeat(64),modelSha256:'d'.repeat(64),
  artifactSha256:sha,proposalNonce:nonce,reviewedAt:'2026-10-09T19:00:00Z',
  walls:5,symbols:2,units:'ft',localParserExecuted:true,preflightPassed:true,
  recipientAppAccepted:false,projectImported:false,humanApprovalGranted:false,
  transportEnabled:false,actionAuthorized:false,signed:false,authenticatedRecipient:false,
  proofScope:'operator-run-local-source-replay-only',
};
const check=x=>checkReplayReport(JSON.stringify(x),preflight);
describe('R10 unsigned parser-replay inspector',()=>{
  it('recognizes a matching local report without granting trust',()=>{
    const out=check(report);
    expect(out.match).toBe(true);
    expect(out.authenticated).toBe(false);
    expect(out.approved).toBe(false);
    expect(out.imported).toBe(false);
  });
  it('rejects mismatched exact digest, nonce or geometry',()=>{
    expect(()=>check({...report,artifactSha256:'e'.repeat(64)})).toThrow('does not match');
    expect(()=>check({...report,proposalNonce:'0'.repeat(32)})).toThrow('does not match');
    expect(()=>check({...report,walls:4})).toThrow('geometry');
  });
  it('rejects authority inflation, signatures and claims of recipient acceptance',()=>{
    for(const update of [
      {signed:true},{authenticatedRecipient:true},{recipientAppAccepted:true},
      {actionAuthorized:true},{projectImported:true},{preflightPassed:false}
    ]) expect(()=>check({...report,...update})).toThrow('unsupported claim');
  });
  it('rejects empty/invalid/fake files and no preflight',()=>{
    expect(()=>checkReplayReport('bad',preflight)).toThrow('Invalid');
    expect(()=>checkReplayReport(JSON.stringify(report),null)).toThrow('First preflight');
    expect(()=>check({...report,parserSha256:'bogus'})).toThrow('digests');
  });
});
