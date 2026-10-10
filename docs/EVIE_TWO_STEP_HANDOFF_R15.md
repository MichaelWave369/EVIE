# R15: EVIE Hooks → Distribution (local and manually gated)

## Proven contract

The new configured workflow `local_hooks_to_distribution_review` consists of exactly `hooks_generator` followed by `distribution_generator`. Neither executes automatically. The real v2 `DistributionGenerator` consumes the first five original R14 hooks via `workflow_step_metadata.hooks_generator.hooks`, producing `hooks_used`, `tiktok_hooks`, and a set of editable local distribution text drafts.

## Step 1: Generate and review hooks

Create a UTF-8 `draft.txt` with 20–8192 bytes, then run from a trusted EVIE checkout:

    python -m tools.evie_supervised_hooks local_content_hooks_review --script-file ./draft.txt --topic "EVIE Creator Loop" --stage-dir ../evie-hooks-review-001 --confirm-local-execution

Inspect the resulting `nine-hooks.json` and `review-receipt.json`. Reject or regenerate anything questionable. Editing the staged hooks after generation invalidates its digest; regenerate from edited script if necessary.

## Step 2: Confirm exact artifact and run the second module

Copy the `artifactSha256` field from the R14 receipt, confirm it matches the actual reviewed JSON, and explicitly supply that digest:

    python -m tools.evie_supervised_distribution --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --confirm-local-execution

Use fresh stage directories outside Git. This command verifies current source hashes, R14 governance flags, exact first-stage bytes and digest, accepted nine-hook format, and unchanged sources before and after running the real `DistributionGenerator` in a temporary Python child. It never invokes the general EVIE workflow runner.

Stage 2 outputs exactly `distribution-draft.json`, `workflow-preflight.json`, and `distribution-review-receipt.json`. The distribution artifact must contain the first five hooks without changes. The preflight document remains an unexecuted *plan*; the separate R15 receipt records a local second-step observation.

## Browser review

EVIE public site → Mission Control → Workflow Studio → Local Hooks To Distribution Review → Content Handoff Studio. Select the original R14 receipt and hooks JSON plus the R15 distribution receipt and distribution JSON. All four are checked locally for source hashes, artifact hashes, five-hook equivalence, and denied authority claims. No file is uploaded.

## Governance and limitations

- An exact SHA-256 plus explicit command flag is an **operator checkpoint**, not independent human identity or cryptographic signature.
- The unsigned receipts can be forged together by someone controlling files. They do not prove process integrity.
- No auto-publishing, post scheduling, sending, cloud-model use or other EVIE workflows are enabled here.
- Draft marketing copy may contain false statements such as something already being shipped. Review and edit *all* claims before use.
- Child processes are time-bound with reduced environments but are **not operating-system network/filesystem sandboxes**.
- Stage-1 bundles from an older workflow registry have a different source digest and must be regenerated after the merge.
- Manual two-command sequence with real artifact consumption does not constitute permission to run arbitrary multi-step automation.

## Tests

`pytest -q tests/test_supervised_distribution.py` runs both genuine producers, checks exactly five handed-off hooks and rejects tampering, missing approval, unknown sources, credential leakage and overwriting. `cd web && npm test && npm run build` covers the four-file browser review and static manifest provenance.
