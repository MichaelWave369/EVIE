# EVIE R10: OpenBlue recipient parser replay

## What changed
EVIE's R9 preflight validates an artifact using EVIE's own mirror of OpenBlue's grammar. **R10 runs the actual `parseEvieProposal` export from OpenBlue's selected local source checkout**, after EVIE preflight passes, without modifying OpenBlue's repository, running the browser UI, or importing a drawing.

An additional GitHub Action checks out `MichaelWave369/OpenBlueprintStudio` at the deliberately pinned commit `015845851191b21764da435ac05f45ccc3779d7b` and executes the exact OpenBlue parser against EVIE's genuine JSON demo fixture. This is a deterministic **parser compatibility test** of that version, not a test of the latest OpenBlue or a claim of UI approval.

## Local replay
Use a locally trusted copy of OpenBlue. The script **imports and runs its JS source inside your Node process**, so do not point it at untrusted or arbitrary code. The checkout must have a clean `src/evieBridge.js`, `src/model.js` and `package.json` relative to the selected git revision.

From the EVIE repository root:

    git -C ../OpenBlueprintStudio rev-parse HEAD

Record the exact 40-character commit SHA you trust, then run:

    node tools/openblue_parser_replay.mjs --openblue-dir ../OpenBlueprintStudio --expected-revision YOUR_VERIFIED_40_CHARACTER_SHA --proposal ./review.proposal.json --artifact ./plan.json --receipt ./openblue-parser-replay.json

The script rejects source revision mismatches, dirty parser files, altered artifact SHA-256, expired review envelopes, invalid geometry and parser rejection. The receipt file is **optional and never overwritten**. Without --receipt it prints a sanitized report to stdout only.

To generate a fresh R8B envelope for the actual blueprint file:

    python -m tools.evie_family_gate prepare --target openblue --kind openblueprint.evie-proposal/1 --artifact ./plan.json --proposal ./review.proposal.json

R8B review envelopes expire quickly (15 minutes by default). Recreate the envelope if your local replay is delayed.

## What the replay receipt is and is not
Schema: `evie.openblue-parser-replay/1`.
Records the operator-selected OpenBlue commit, parser and model SHA-256, artifact SHA-256, review nonce, date, and observed counts.
It sets `recipientAppAccepted:false`, `projectImported:false`, `humanApprovalGranted:false`, `transportEnabled:false`, `actionAuthorized:false`, `signed:false`, and `authenticatedRecipient:false`.

This is **operator-run evidence that selected recipient parser source executed**, not a receipt issued by the running OpenBlue app, and not cryptographic proof of host integrity. It is not recipient acceptance, and the unsigned report may be forged. A reproducible pinned CI run is stronger compatibility evidence than a self-reported file, but still does not prove real UI acceptance. OpenBlue's existing in-app Import → Preview → Approve remains mandatory.

## CI
The `EVIE OpenBlue Parser Contract Replay` action checks out both repositories with read-only GitHub permissions and runs `node --test tests/openblue_parser_replay.test.mjs` against an explicitly pinned recipient revision. It intentionally does not require external service secrets, API keys or a browser; no Blue repo files are written.

## Browser follow-up
EVIE's Family Gate can compare a local unsigned replay receipt to a successful R9 file preflight, matching nonce, artifact digest and stated test outcomes. This never establishes trusted identity or automatic delivery, and the global live-qualified count remains zero.

## Known gaps
Untrusted recipient JS can execute arbitrary code inside Node; this harness is not a sandbox. Pin only reviewed source. The CI check covers the pinned revision; newer OpenBlue commits require deliberate review and pin updates. No external transport or automatic project mutation is implemented.
