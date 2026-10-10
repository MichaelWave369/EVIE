# EVIE R24: Read-only Operator Identity and Protected-State Groundwork

## Purpose

R23 established that authenticated HTTP execution is NOT qualified. Its six blockers remain explicitly unsatisfied. R24 adds **platform-native read-only observations** about the process inspecting a local bearer token and/or nonce-ledger file. It does not establish a service-side execution identity or safe persistent approval store; these require OS privilege separation and durable write-control boundaries.

## Operator command

From a trusted local EVIE checkout:

    python -m tools.evie_operator_state inspect --token-file ../evie-local-service.token --ledger-file ../evie-local-lease-ledger.sqlite

Pass either file path or both. Missing files are recorded as missing, not created. Nothing is read from the token file or database. The JSON response intentionally excludes absolute file paths, usernames, actual user SIDs, bearer tokens and SQL rows. It includes `httpExecutionAllowed:false` and `serviceSideStoreProtected:false` unconditionally. It does not launch a worker or Docker, sign a lease, run a server, write a report or edit an ACL.

## Real OS branches

### Windows (native APIs, tested on windows-latest)

- `OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY)` and `GetTokenInformation(TokenUser)` obtain the executing process's user SID in memory.
- `GetNamedSecurityInfoW(SE_FILE_OBJECT, OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION)` obtains a candidate file's owner SID and DACL pointer.
- `EqualSid` compares process token and file-owner SID, returning **only a boolean**. Win32 buffers and handles are released with `LocalFree` and `CloseHandle`.
- `windowsDaclPresent` only states that a non-null DACL was observed. **It is NOT an effective-rights calculation**: group membership, inherited allow/deny entries, privilege elevation, Windows ACL inheritance and service accounts can all affect access.
- No ACL is modified. No Windows file is described as privately protected; `effectiveWindowsAclPrivacyVerified:false` stays false.

### Linux/Unix POSIX branch

- Observes `lstat` on a candidate regular file and its immediate parent without reading contents.
- Requires bounded file size, owner matching `geteuid`, a private immediate parent owned by the same user, no group/world permission bits on the file, and a single link for `candidateFilePrivateByPosixBits`.
- Symbolic links, hardlinks, unexpectedly large or missing objects, invalid type and public file/parent modes fail the **candidate** check.
- These are local discretionary access observations, not proof against root, malicious local code, a compromised kernel, directory races or tamper-proof SQLite state.

## Explicit nonclaims

| Claim | R24 result |
|---|---|
| Current process owner matches candidate file owner | Observed boolean only |
| Windows DACL present | Observed boolean only; effective ACL rights NOT calculated |
| POSIX candidate file appears private by immediate owner/mode bits | Conditional observation only |
| HTTP request authenticated to OS user | **NO** |
| Service running separately from local host authority | **NO** |
| Approval/nonce file protected from replacement | **NO** |
| Signed execution receipt independently trusted | **NO** |
| HTTP execution or publication authorized | **NO** |

R22's `GET /v1/security` remains a source-bound, **static default-deny report**; it does not accept local path arguments, expose file metadata or dynamically raise its own privileges. The public GitHub Pages web guide never contacts localhost. A Windows-only dedicated CI job now validates the real native process SID/DACL observation. The existing Python release gate, React build and signed two-stage Docker gate remain required.

## Trust and privacy boundaries

This is a file-metadata inspector, not a complete Windows ACL auditor, identity provider or Windows service installation routine. Observed owner equality can occur while other group principals retain permissions. Windows effective access needs a future native `AuthzAccessCheck`/`AccessCheck` design with documented target principals and tests, ideally followed by ACL provisioning and a real separate service principal. Never interpret an arbitrary `icacls` string or a host-side admin process as a verified HTTP client identity.

The R23 blockers stay at `satisfied:false`. No HTTP `POST` endpoints, automatic signing, endpoint to accept file paths, OS privilege escalation, local daemon scheduling, ACL chmod repair, or publishing behavior is added.

## Tests and promotion criteria

Run `python -m pytest -q tests/test_operator_state.py` locally. Tests cover missing/oversized/symlinked/hardlinked files, non-disclosure of token content/path, POSIX public/private mode/parent checks, native Windows token-owner/DACL calls when on Windows, no-write behavior, CLI allowlist and blanket denial of HTTP execution. GitHub adds `EVIE R24 Windows Operator State` on `windows-latest`, while the existing dedicated offline Docker gate now runs the platform-neutral tests on Linux.

Follow-on work should include independently tested Windows effective ACL access checks, safe token/ledger provisioning for a dedicated service account, a protected write path for a replay ledger, authenticated IPC/peer credentials and mandatory migration away from legacy host-run CLIs. None of these are implemented here.
