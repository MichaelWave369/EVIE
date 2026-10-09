import { describe, expect, it } from 'vitest';
import { generateKeyPairSync, createHash, sign, webcrypto } from 'node:crypto';
import manifest from './generated/mission-control.json';
import { verifyTrustedAttestation } from './attestationVerify.js';

const base64 = data => Buffer.from(data).toString('base64');
function sample() {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519');
  const pem = publicKey.export({ type: 'spki', format: 'pem' });
  const der = publicKey.export({ type: 'spki', format: 'der' });
  const fingerprint = createHash('sha256').update(der).digest('hex');
  const receipt = {
    schemaVersion: 'evie.qualification-receipt/1', module: 'openblueprint_floor_plan',
    scenario: 'cad_rectangular_concept_v1', status: 'pass',
    origin: 'local-subprocess-observation', createdAt: '2026-10-09T12:00:00Z',
    durationMs: 100, sourceSha256: manifest.qualificationFixtures[0].sourceSha256,
    artifactSha256: 'a'.repeat(64),
    checks: Object.fromEntries(['versioned_proposal', 'versioned_project', 'bounded_wall_geometry',
      'symbol_types', 'unique_element_ids', 'source_labels', 'run_id_bound', 'digest_match',
      'artifact_scope'].map(id => [id, true])),
    effectPolicy: { allowlisted: true, temporaryWorkspace: true, providerEnvironmentStripped: true,
      networkSandboxEnforced: false, externalEffectsAuthorized: false },
    trust: { signed: false, authenticatedMachine: false },
  };
  const signedRecord = JSON.stringify({ signedAt: '2026-10-09T12:01:00Z', receipt });
  const payload = Buffer.from(signedRecord, 'utf8');
  const signature = sign(null, Buffer.concat([Buffer.from('EVIE/QUALIFICATION_ATTESTATION_V1\0'), payload]), privateKey);
  return {
    pem, privateKey,
    attestation: {
      schemaVersion: 'evie.qualification-attestation/1', algorithm: 'Ed25519',
      keyFingerprint: fingerprint, payloadBase64: base64(payload), signatureBase64: base64(signature)
    },
  };
}
const verify = (a, pem) => verifyTrustedAttestation(JSON.stringify(a), pem, manifest, webcrypto);

describe('R8 independently selected public-key signature verification', () => {
  it('accepts a valid Ed25519 attestation while refusing job authority', async () => {
    const { pem, attestation } = sample();
    const result = await verify(attestation, pem);
    expect(result.signatureValid).toBe(true);
    expect(result.sourceMatch).toBe(true);
    expect(result.actionAuthorized).toBe(false);
    expect(manifest.summary.runtimeQualifiedModules).toBe(0);
  });
  it('rejects wrong trust root, tampered payload and tampered signature', async () => {
    const { pem, attestation } = sample();
    const other = sample().pem;
    await expect(verify(attestation, other)).rejects.toThrow('not the selected');
    const altered = { ...attestation, payloadBase64: base64('{}') };
    await expect(verify(altered, pem)).rejects.toThrow(/signature size|INVALID/);
    await expect(verify({ ...attestation, signatureBase64: base64(Buffer.alloc(64)) }, pem)).rejects.toThrow('INVALID');
  });
  it('rejects malformed and unsupported files before any trust claim', async () => {
    const { pem, attestation } = sample();
    await expect(verify({ ...attestation, algorithm: 'none' }, pem)).rejects.toThrow('Unsupported');
    await expect(verify(attestation, '-----BEGIN PRIVATE KEY-----abc-----END PRIVATE KEY-----')).rejects.toThrow('PUBLIC KEY');
    await expect(verifyTrustedAttestation('{oops', pem, manifest, webcrypto)).rejects.toThrow('malformed');
  });
});
