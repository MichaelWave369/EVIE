# EVIE Capability Qualification Lab · Rung 7

## Aim
Progress EVIE from registered to tested against a fixed scenario without mistaking 117 registered Python modules for 117 verified-running capabilities. Only ONE scenario is allowlisted here. No arbitrary module runner is created.

## Operator commands
From the EVIE repo root with Python dependencies installed:

    python -m tools.evie_qualify list
    python -m tools.evie_qualify run openblueprint_floor_plan
    python -m tools.evie_qualify run openblueprint_floor_plan --receipt ./cad-qualification.json

The first lists allowlisted scenarios. The second runs only the CAD fixture and prints a sanitized JSON report. The third additionally writes a NEW receipt at a path you explicitly choose. Existing files are never overwritten. Do not commit local qualification receipts, private runtime metadata or credentials to the public repository.

The worker exercises the real OpenBlueprintFloorPlanModule.generate method with a 24 × 16 ft concept room, checks wall/partition geometry, door/network symbols, unique IDs, versioned formats and the proposal SHA-256 integrity digest.

## Isolation and limits
- Separate Python subprocess using -I, an allowlisted fixed source root and entrypoint, disposable cwd and a small credential-free environment allowlist.
- Fixed inputs, 15-second default timeout, 30-second hard maximum. Never auto-executes publishing, LLM APIs or other modules.
- Temporary artifacts are checked and destroyed. Only sanitized summary fields leave the child process.
- **Not a hard security sandbox.** Network isolation is NOT enforced by OS policy, and a malicious codebase can bypass process/environment safeguards. Run only audited fixtures.

PASS means ONE fixture executed successfully in THAT environment. It does not mean certified CAD, production-readiness, model access, safe publishing, or trusted identity.

## Receipt governance
Schema: evie.qualification-receipt/1.
Contains module/scenario ID, named checks, status, source-file SHA-256, discarded proposal SHA-256, timestamp, duration and policy claims; explicitly signed:false and authenticatedMachine:false. No paths, API keys, runtime environment details, logs or raw output.

The React Mission Control has a browser-only receipt inspector comparing the source checksum with the public build's source. It never uploads, stores, runs or trusts the file as independently authenticated evidence. The global count of live-qualified capabilities stays zero. A malicious file can forge a receipt, including the hash.

## Follow-up
Strong isolation and trusted receipts, staged per-module replay, approved leases/budgets and opt-in execution for new allowlisted modules.

Tests: pytest -q tests/test_evie_qualification.py; cd web && npm test.
