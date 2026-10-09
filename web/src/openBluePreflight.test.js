import { describe, expect, it } from 'vitest';
import { webcrypto } from 'node:crypto';
import { createFamilyProposal } from './familyGateLogic.js';
import catalog from './generated/family-targets.json';
import { createDemoProposal } from './blueprint.js';
import { inspectOpenBlueHandoff } from './openBluePreflight.js';

const at = new Date('2026-10-09T19:01:00Z');
async function fixture() {
  const artifact = createDemoProposal({width:24,depth:16,partition:'vertical'});
  const bytes = new TextEncoder().encode(JSON.stringify(artifact));
  const sha = Buffer.from(await webcrypto.subtle.digest('SHA-256', bytes)).toString('hex');
  const envelope = createFamilyProposal({
    target:'openblue',artifactKind:'openblueprint.evie-proposal/1',size:bytes.length,
    sha256:sha,createdAt:'2026-10-09T19:00:00Z',nonce:'a'.repeat(32),
  },catalog);
  return {envelope,artifact,bytes};
}

describe('R9 OpenBlue digest-bound local file preflight',()=>{
  it('passes an authentic EVIE-format fixture but never claims OpenBlue accepted it',async()=>{
    const {envelope,bytes}=await fixture();
    const report=await inspectOpenBlueHandoff(envelope,bytes,webcrypto,at);
    expect(report.result).toBe('preflight_pass');
    expect(report.walls).toBe(5);
    expect(report.symbols).toBe(2);
    expect(report.recipientAccepted).toBe(false);
    expect(report.executionAuthorized).toBe(false);
    expect(report.transportEnabled).toBe(false);
    expect(report.authenticated).toBe(false);
  });
  it('rejects tampered bytes and wrong destination or expired envelope',async()=>{
    const {envelope,bytes}=await fixture();
    const changed=new Uint8Array(bytes);
    changed[changed.length-3]=changed[changed.length-3]===32?10:32;
    await expect(inspectOpenBlueHandoff(envelope,changed,webcrypto,at)).rejects.toThrow('SHA-256');
    await expect(inspectOpenBlueHandoff({...envelope,target:'phios'},bytes,webcrypto,at)).rejects.toThrow('not for OpenBlue');
    await expect(inspectOpenBlueHandoff(envelope,bytes,webcrypto,new Date('2026-10-09T20:00:00Z'))).rejects.toThrow('expired');
  });
  it('rejects invalid geometry even when SHA-256 has been recomputed',async()=>{
    const {envelope,artifact}=await fixture();
    artifact.project.walls[0].x2=0;
    const bytes=new TextEncoder().encode(JSON.stringify(artifact));
    const sha=Buffer.from(await webcrypto.subtle.digest('SHA-256',bytes)).toString('hex');
    await expect(inspectOpenBlueHandoff({...envelope,artifactBytes:bytes.length,artifactSha256:sha},bytes,webcrypto,at)).rejects.toThrow('geometry');
  });
  it('rejects action requests and blank source identifiers',async()=>{
    const {envelope,artifact,bytes}=await fixture();
    await expect(inspectOpenBlueHandoff({...envelope,requestedEffects:['publish']},bytes,webcrypto,at)).rejects.toThrow('execution');
    artifact.source.runId='';
    const modified=new TextEncoder().encode(JSON.stringify(artifact));
    const sha=Buffer.from(await webcrypto.subtle.digest('SHA-256',modified)).toString('hex');
    await expect(inspectOpenBlueHandoff({...envelope,artifactBytes:modified.length,artifactSha256:sha},modified,webcrypto,at)).rejects.toThrow('source');
  });
});
