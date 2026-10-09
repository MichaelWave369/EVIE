# EVIE R8B: Family Gate (Review, Not Execution)

## What exists
A fail-closed local proposal and signed-review contract for intended artifact handoff between EVIE and OpenBlue, FieldDeck, PhiOS, SuperPhiVessel, PixelForge and Domistika. The canonical contract catalog is `app/family_gate/family_targets.json` and is consumed by the Python gate and React build. These are proposed artifact format relationships, **not live connectors**.

The static GitHub Pages Family Gate view can hash a user-selected local artifact in-browser and export `evie.family-handoff-proposal/1` with target, kind, SHA-256, byte count, random 128-bit nonce, UTC timestamps, 15-minute expiry, and explicitly disabled effects/transport/execution. Maximum artifact size is 8 MiB. File content is not uploaded.

## Local CLI
From the EVIE repository root:

    python -m tools.evie_family_gate catalog

To prepare a fresh, review-only file envelope:

    python -m tools.evie_family_gate prepare --target openblue --kind openblueprint.evie-proposal/1 --artifact ./your-plan.json --proposal ./handoff.proposal.json

To acknowledge using your independently created, passphrase-encrypted R8 Ed25519 key:

    python -m tools.evie_family_gate acknowledge --proposal ./handoff.proposal.json --signing-key ./evie-local.pem --ack ./handoff.ack.json

To verify using a separately selected and trusted PUBLIC key:

    python -m tools.evie_family_gate verify --ack ./handoff.ack.json --trusted-public ./evie-trusted.pub.pem

All outputs are explicit new filenames, written without overwrite; no network requests or target app invocations occur. The private passphrase is entered via local getpass and never passed as a command line argument.

## Governance requirements
- Only known target/artifact pairs are accepted. The catalog never proves target support.
- Handoff proposals allow only `manual_inspection_only`. Requested effects are empty, execution authorization is false, and transport enabled is false. Unexpected fields and action requests fail validation.
- Expiration is 1–30 minutes. Validation rejects expired proposals and far-future timestamps (2-minute clock skew). An acknowledgement is valid only within the original proposal's expiry and against the selected public key.
- Review signatures have a separate domain string from qualification attestations. Mixing R8 signature payloads with R8B review data must fail.
- A digest binds bytes but cannot prove the payload is safe, accurate, received or acceptable to a recipient.
- A signed acknowledgement is not a grant; there is no one-time consumption ledger, nonce-replay enforcement, recipient authentication, API transport or cross-project acceptance proof.
- No browser action reaches localhost or sends the private file to GitHub Pages.

## Intended family routes (all NOT IMPLEMENTED)
OpenBlue: OpenBlueprint concept JSON; FieldDeck: workflow deck draft; PhiOS: qualification receipt; SuperPhiVessel: signed attestation; PixelForge: concept geometry proposal; Domistika: creative workflow draft.

These are experimental review-envelope formats only. Recipient adapters must be separately specified, versioned and tested. Existing independent OpenBlue import functionality is not activated by the Family Gate.

## Next rung
R9 should add an explicit recipient-side **read-only validation adapter** for a single project, with fixture replay, independently acknowledged human approval and denial by default. No additional remote effectful adapters until transport authentication, budgets, consent, replay protection and audit receipts are independently verified.

## Tests
`pytest -q tests/test_evie_family_gate.py`
`cd web && npm test && npm run build`
