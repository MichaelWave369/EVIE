# EVIE R8: Signed Qualification Evidence (Ed25519)

## Goals and boundaries
R7 introduced a fixed local CAD scenario and unsigned self-reported receipts. R8 adds signatures and an independently selected public-key trust root. It does not add OS-level sandboxing, external publishing authority, or family-bridge job execution.

## Generate a local encrypted Ed25519 keypair
From the EVIE repository root with dependencies installed (cryptography is already in requirements):

    python -m tools.evie_attest keygen --private ./evie-local.pem --public ./evie-trusted.pub.pem

EVIE prompts twice for a passphrase of at least 12 characters. The private key is encrypted in PKCS#8 PEM. Both filenames must be unused; existing files are never overwritten. Record the displayed fingerprint (SHA-256 of DER SPKI) in an independent trusted location. Prefer keeping signing keys outside the repository and restrict access. Never publish a signing private key.

## Run one allowlisted test and sign immediately

    python -m tools.evie_qualify run openblueprint_floor_plan --signing-key ./evie-local.pem --attestation ./cad-run.attestation.json

Only a fresh PASS from the existing fixed 24×16-foot CAD scenario is eligible. Signing is performed in the parent process after the child qualification finishes, with the signing key and passphrase never passed to the worker. The key does not permit running any other module. Optional --receipt ./cad-run.qualification.json preserves the original unsigned R7 receipt separately. Output files are created exclusively, never overwritten.

## Verify against an independently chosen trusted key

    python -m tools.evie_attest verify --attestation ./cad-run.attestation.json --trusted-public ./evie-trusted.pub.pem

Verifier requirements:
- Envelope schema evie.qualification-attestation/1, Ed25519 only.
- The signed payload is a canonical UTF-8 JSON record containing signedAt and the original R7 receipt, with domain separation via prefix EVIE/QUALIFICATION_ATTESTATION_V1 followed by a NUL byte.
- The key fingerprint must match the public key selected by the verifier, and the Ed25519 signature must validate.
- The receipt must match the allowlisted scenario, all required PASS checks, safe-effect claims, and the currently checked-out source file SHA-256.
- Verified output always sets actionAuthorized=false.

Browser verification is also available in Mission Control → Qualification Lab. Select the attestation and trusted public PEM separately; modern browsers verify via WebCrypto. There are no uploads, persistence, remote API calls or action grants. Use the Python verifier if Ed25519 WebCrypto is unsupported.

## Trust and limitations
A valid signature proves control of the selected key over those bytes. It does not establish the operator's legal identity, prove the worker ran, certify a CAD design, prevent signer compromise, confirm real-world safety, or authorize any action. The R7 child process is NOT a hard network or OS sandbox. GitHub Pages claims zero authenticated live-qualified modules. Do not take a public key embedded alongside untrusted evidence as a trust root.

## Family bridge roadmap
Follow-on work requires separate, time- and budget-scoped grants, independent replay evidence, non-replayable actions, stronger isolation and explicit human permission before EVIE can connect effectful jobs to FieldDeck, PhiOS, SPV, PixelForge or publishers. Signed PASS alone NEVER unlocks execution.

## Tests
pytest -q tests/test_evie_attest.py
cd web && npm test
CI also executes full Python and React build suites.
