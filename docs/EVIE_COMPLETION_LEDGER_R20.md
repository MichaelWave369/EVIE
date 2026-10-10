# EVIE R20: Execution Exposure Audit and Completion Evidence Ledger

## What is qualified, and what is not

R20 adds a strictly **read-only local auditor** for the R19 governed two-stage content workflow. It never executes modules, calls Docker, signs anything, consumes a nonce, creates or modifies SQLite state, writes a report file, publishes or authorizes subsequent jobs.

**Three distinct claims are checked:** (1) source-bound staged artifact integrity, (2) independently selected Ed25519 lease scope and signature, and (3) local evidence of a nonce spent before a distribution draft run. The source event and receipt files remain **unsigned self-reported local observations**. Matching them, even with a signed lease, does not independently prove the host executed Docker without modification.

## Known execution lanes: source-only inventory

From the EVIE checkout run:

    python -m tools.evie_completion_audit entrypoints

This inspects the current source of exactly six known local CLI lanes, recording each file's SHA-256 and declared command-level requirements for signing and Docker. It explicitly identifies legacy host Python lanes: R14 standalone hooks, R15 standalone hash-approved distribution, R16 signed host distribution and the fixed CAD fixture. R17 signed Docker stage 2 and R19 governed dual-Docker controller are separately identified.

**This is an explicit source inventory, not a whole-repo call graph, an executable permission-enforcement layer, or proof that unrelated code cannot run.** The old commands still exist. There is no claim that merely adding a better route revokes an older CLI.

## Read-only session audit

After creating your own R19 governed session, run:

    python -m tools.evie_completion_audit session --session-dir ../evie-flow-session-001

The report checks current workflow source, first-stage receipt, original nine hooks, SHA-256, code hashes, source isolation metadata and the controller's sequenced events. When stage 2 exists it additionally checks the actual downstream JSON, its SHA-256, exact first-five-hook consumption, distribution module hashes, its receipt and the unsigned local lease-consumption observation.

Without independently supplied signing evidence, a staged draft remains **DRAFT_STAGED_APPROVAL_UNVERIFIED**. It never becomes fully verified merely because JSON fields claim `signed=true` or `localNonceConsumed=true`.

For a completed session, provide the **separately chosen trusted public key**, historical signed lease and *existing* nonce ledger:

    python -m tools.evie_completion_audit session --session-dir ../evie-flow-session-001 --lease-file ../evie-flow-lease-001.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite

The auditor verifies the signed action, exact first artifact, current source and completed directory fingerprint against the lease. It checks the **recorded attempt timestamp** against the signed validity window and uses a **read-only SQLite connection** (`mode=ro`, `query_only=ON`) to locate the spent nonce and exact artifact digest. An absent ledger is rejected and never created. The recorded attempt time is itself a mutable **local observation**, not trusted time evidence. A lease may have expired now but have been valid at its recorded execution time.

R20 introduces `historical_completed=True` as an explicit, read-only verification mode on the existing lease verifier. **The original execution verifier retains the strict default:** it refuses destination directories that already exist. The audit flag does not authorize execution or staging.

## Completion contract statuses

| Status | Meaning |
|---|---|
| `WAITING_FOR_REVIEW` | Valid original hooks were staged but no attempt recorded |
| `ATTEMPT_OUTCOME_UNKNOWN` | The controller recorded an attempted Stage 2, but there is no valid completion event; no retry or success promotion |
| `DRAFT_STAGED_APPROVAL_UNVERIFIED` | Both actual artifacts and local receipts match, but independently selected signed/ledger evidence was not supplied |
| `LOCAL_DRAFT_CONTRACT_VERIFIED` | Actual source/output artifact integrity plus the supplied trusted public key, signed historical scope and spent nonce in the selected local ledger all match |
| `EVIDENCE_REJECTED` | Malformed, changed, missing, unauthorized or mismatched evidence fails closed |

**No R20 status means published, accepted, externally authenticated, final product DONE, or permission to execute new actions.** The narrow completion contract is only `local_two_stage_draft_handoff_only`. The report always states `finalProductDone:false`, `publishingAuthorized:false`, `editorialAcceptanceVerified:false` and `noRuntimeExecutedByAuditor:true`.

## Evidence limitations and threat model

- The local controller's events and consumption receipt are self-reports; a malicious operator controlling the computer and artifacts can forge or reset them.
- Possession of the independent Ed25519 signing key proves that key signed the lease, **not** a person attended or fact-checked the content.
- The `spent_local_leases` row is only meaningful in the same intact, trusted local SQLite file. Other ledger copies, an attacker with filesystem write access or old host-run CLIs can bypass one-use controls.
- The Docker profiles are local policy metadata and were tested independently in R17/R19 CI; an individual runtime's unsigned receipt is not a secure machine attestation.
- The historical lease's `attemptedAt` was recorded by the local runtime. It is not an independently trusted clock.
- The auditor only inspects the explicit file contract and known entrypoints. It does not automatically certify every module, source path, network operation or system permission.

## Tests

`pytest -q tests/test_completion_audit.py` covers source inventories, stage-one pause, uncertain attempt, successful original two-module handoff, independent signer/ledger matching, tamper rejection, unreadable/missing ledger and unchanged execution-time verifier semantics. The R19 dedicated real-Docker CI now ALSO calls this auditor on the genuinely isolated two-module workflow to qualify the limited draft contract. React Pages builds the static Completion Ledger Guide, which only supplies copyable local commands.

## Future

To make this a mandatory execution policy, design a single local service with OS-enforced access separation, authenticated signers, protected persistent ledger and explicit migration/deprecation of direct legacy entrypoints. Do not confuse the R20 read-only auditor with that service.
