# EVIE R16 · Local Ed25519 action leases (optional signed lane)

## Purpose

R15 gave EVIE its first real two-step content draft: `hooks_generator` → human SHA-256 review → `distribution_generator`. Its existing CLI requires a reviewed SHA-256 and explicit `--confirm-local-execution`, but **neither authenticates a signer nor prevents reuse on a different output folder**. R16 introduces a **separate, opt-in signed lane**, rather than silently changing or pretending to protect the old command.

The new `evie.local-action-lease/1` is a short-lived Ed25519 signature with **a new cryptographic domain** distinct from qualification attestations and family handoff acknowledgements. An operator explicitly selects a trusted public key independent of the signed lease.

The signed payload includes:
- One action, `local_distribution_draft_only`, and exact workflow `local_hooks_to_distribution_review`
- Exact R14 `artifactSha256` and current EVIE workflow-registry source digest
- SHA-256 of the intended absolute new stage directory (path undisclosed in lease)
- Random 128-bit nonce; UTC issue and expiry (5-minute default, maximum 10 minutes)
- Maximum wall-time for the second module (default 20 seconds, maximum 20); artifact limit of 32,768 bytes; maximum one use
- `externalEffectsAuthorized:false` and `recipientAccepted:false`

All parameters are signed together. Unsupported fields, expired leases, wrong keys, wrong actions, wrong source/byte hashes, changed destination, future stamps and elevated effect claims are rejected.

## Setup

From a trusted EVIE checkout, create local Ed25519 keys once. This reuses EVIE's existing encrypted key generator:

    python -m tools.evie_attest keygen --private ../evie-lease-private.pem --public ../evie-lease-trusted-public.pem

The CLI prompts for a strong encryption passphrase. The private signing key must not be uploaded, checked into Git or passed to a subprocess. Choose the trusted **public** key from a location you control; never rely on a public key or fingerprint embedded in the untrusted lease to decide who is trusted.

## Stage 1 (existing R14)

Prepare your UTF-8 `draft.txt` and run:

    python -m tools.evie_supervised_hooks local_content_hooks_review --script-file ./draft.txt --topic "EVIE Creator Loop" --stage-dir ../evie-hooks-review-001 --confirm-local-execution

Review the contents of `nine-hooks.json`. Copy the 64-character `artifactSha256` from the corresponding `review-receipt.json`. If the hooks contain claims that must be edited, modify your source script and **regenerate** Stage 1 rather than changing the hashed artifact.

## Sign a bounded Stage 2 approval

    python -m tools.evie_action_lease issue --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --signing-key ../evie-lease-private.pem --lease-file ../review.lease.json

Signing requires the encrypted private-key passphrase entered interactively, not on the command line. EVIE checks the original R14 bundle and current source version before issuing. The signed JSON is written only to a **new file**, never overwritten.

You can independently verify the signature and scope without consuming it or starting a module:

    python -m tools.evie_action_lease verify --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --lease-file ../review.lease.json --trusted-public ../evie-lease-trusted-public.pem

This inspection does **not** check the nonce ledger or prove the lease has not already been spent.

## Spend once, execute locally and stage reviewed output

    python -m tools.evie_approved_distribution --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --lease-file ../review.lease.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution

The signer grants the narrow local distribution-draft attempt only. The runner:
1. Revalidates the R14 hooks/receipt, EVIE source and target destination.
2. Verifies the Ed25519 signature using the independently chosen trusted key, expiry and bounded local execution policy.
3. **Atomically spends the nonce in the operator-selected SQLite ledger before launching Stage 2.** Duplicate or simultaneous use of that nonce against the **same intact ledger** is denied.
4. Invokes the existing R15 real `DistributionGenerator` under the narrower signed timeout.
5. Stages R15's three files plus `lease-consumption.json`, an **unsigned local observation** indicating signature verification and local nonce consumption.

An exception, crash, timeout, stale output folder or failed Stage 2 after nonce consumption **burns the lease**; to retry, inspect the failure, create a new output folder and sign a fresh lease. No automatic retry or refund of consumed permissions.

## Scope of the guarantee

- **One-use is enforced only within the same trusted, intact local SQLite ledger.** Back up and protect it appropriately, always use the same path, and never reset or duplicate the ledger as a way around controls. If someone can delete/rewrite the ledger, or use a separate host/ledger, this is **not** a globally non-replayable permission system.
- The signing key only establishes possession of that key. It does not prove the signer's legal identity, attendance, independent review of claims, or host integrity.
- The older R15 `tools.evie_supervised_distribution` command remains functional and **does not require a signed lease**. This R16 protection is explicitly opt-in, not a repository-wide mandatory enforcement barrier.
- Python subprocesses are time-bounded and credential-stripped but **not OS network/filesystem sandboxes**. Direct access to your trusted checkout can bypass this software workflow.
- This approval NEVER authorizes live distribution, posting, emails, purchases, API tokens, unrestricted modules or future job dispatch.
- All content remains an editable draft and must be fact-checked before publishing.
- Signatures do not make the downstream `lease-consumption.json` execution report cryptographically authenticated. The consumption report explicitly denies that claim.

## Tests and future hardening

`pytest -q tests/test_action_leases.py` exercises a real original R14 → R15 chain through the new signed lane, time limits, signer mismatch, tampering, source/destination/digest changes, expiry, duplicate and concurrent nonce consumption and denial before execution.

A later rung can make signed approvals mandatory for selected executable actions and bind them to a single controlled local service with stronger OS isolation, securely persisted state and authentication, *after* an explicit migration plan. Never claim that this optional local CLI is such a service.
