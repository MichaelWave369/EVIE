# EVIE R11: FieldDeck blueprint handoff (manual, deny-by-default)

## Actual cross-repository contract
EVIE's `evie.deck.draft/1` uses historical Sovereign Shelf card IDs. FieldDeck does NOT accept those as actions. FieldDeck `fielddeck.chain.blueprint` `schema_version:0.5.0` supports the explicitly reviewed action IDs `catalog-health`, `script-smoke`, `macro-demo` and 1–6 steps. Its policy must be `execution:denied`, `requires_authentication:true`, and `requires_review:true`.

This feature makes NO semantic translation of original 159 Shelf cards into runnable FieldDeck actions. It is an independent human-designed blueprint informed by inspection of an EVIE design deck. EVIE does not request a job, create an IssueOps issue, transmit files, grant tokens, or control a FieldDeck executor.

## Browser workflow
1. In EVIE → Full Sovereign Shelf, choose cards in the design-only composer and download the EVIE draft JSON.
2. Open EVIE → Family Gate → EVIE meets FieldDeck; select that EVIE draft file locally. EVIE checks the version, exact draft shape, zero-based card order, catalog membership, lack of duplicates and `executable:false`.
3. Independently select 1–6 reviewed FieldDeck actions. They are not automatically derived from EVIE card meanings. Reorder or remove selected actions.
4. Download a **FieldDeck v0.5 default-deny blueprint**, which exactly fits FieldDeck's `parseBlueprint` shape with no authority-bearing extra fields.
5. Open FieldDeck → Chain Lab and import the blueprint for its own preview, preflight and separate approval process.

The public EVIE site only reads files through the browser's File API and downloads the explicitly chosen JSON. No API call, localStorage history, or permissions are involved.

## Pinned parser replay in GitHub CI
`.github/workflows/fielddeck-contract.yml` checks out **EVIE** and a pinned, read-only **FieldDeck** revision `bc9b73688d8725945d08f1299e5bc0e27e73e710`, and imports the real recipient `src/blueprint-model.mjs` and `src/chain-model.mjs` to verify exact blueprint output and reject forged authority, unknown action IDs and schema extensions. The revision pin is deliberate. Future FieldDeck changes require a reviewed pin update.

Tests: `cd web && npm test && npm run build`; cross-repo: `node --test tests/fielddeck_contract.test.mjs` with FIELDDECK_CHECKOUT and FIELDDECK_REVISION set to a trusted local checkout. The standard EVIE Python release gate runs independently.

## Boundaries
- Source compatibility is not evidence of a live FieldDeck UI import, operator review or approved execution.
- No EVIE Shelf card becomes executable by being listed alongside a FieldDeck action.
- Even FieldDeck's approved diagnostic preset still requires authenticated GitHub IssueOps and the runner's independent policy check.
- No recipient acceptance receipt, cryptographic issuer proof, one-time lease or transport is created in this rung.
- The R8B FieldDeck route continues to support `evie.deck.draft/1` for a standalone review envelope, not a runnable chain.

## Next
Eventually introduce a read-only recipient-side import acknowledgement with independent provenance, without conflating that with action authorization. Expand mappings only after one-to-one semantic contracts and separate safety qualification.
