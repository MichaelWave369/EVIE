"""R24: read-only local OS operator and file-state observations.

Designed to evaluate LOCAL service groundwork, not identify an HTTP client.
It NEVER reads the bearer secret or SQLite content, signs an action, runs Docker,
changes ACLs/chmod, opens HTTP, writes reports, or allows worker execution.

POSIX: observes UID, file modes and immediate parent directory permissions.
Windows: native token-user SID + GetNamedSecurityInfoW owner/DACL inspection.
A present DACL does NOT prove effective access is private; the Windows path
intentionally refuses to certify it. No real SIDs, usernames or file paths are
included in JSON results.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

SCHEMA = "evie.local-operator-state/1"
FILE_TYPES = frozenset(("token", "ledger"))
MAX_SIZE = {"token": 128, "ledger": 2_000_000}
CAPABILITIES = (
    "current_process_principal_observation",
    "regular_file_owner_and_permission_observation",
    "existing_local_candidate_file_inspection",
)
DENIED = (
    "authenticated_http_client_identity",
    "protected_service_side_nonce_store",
    "os_separated_worker_privilege",
    "automatic_file_permission_repair",
    "http_start_resume_or_publish",
)


def _windows_identity_and_owner(path: Path) -> tuple[bool, bool]:
    """Read-only Win32 token and owner SID comparison.

    This does NOT check effective file access for group memberships, inherited
    ACEs or privileges. A DACL's mere presence is NOT a privacy guarantee.
    """
    import ctypes
    from ctypes import wintypes

    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    HANDLE = wintypes.HANDLE
    DWORD = wintypes.DWORD
    PVOID = ctypes.c_void_p

    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = HANDLE
    adv.OpenProcessToken.argtypes = [HANDLE, DWORD, ctypes.POINTER(HANDLE)]
    adv.OpenProcessToken.restype = wintypes.BOOL
    adv.GetTokenInformation.argtypes = [
        HANDLE, DWORD, PVOID, DWORD, ctypes.POINTER(DWORD),
    ]
    adv.GetTokenInformation.restype = wintypes.BOOL
    adv.EqualSid.argtypes = [PVOID, PVOID]
    adv.EqualSid.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # GetNamedSecurityInfoW allocates a descriptor freed using LocalFree.
    adv.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPWSTR, DWORD, DWORD,
        ctypes.POINTER(PVOID), PVOID, ctypes.POINTER(PVOID),
        PVOID, ctypes.POINTER(PVOID),
    ]
    adv.GetNamedSecurityInfoW.restype = DWORD
    kernel.LocalFree.argtypes = [PVOID]
    kernel.LocalFree.restype = PVOID

    class SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("sid", PVOID), ("attributes", DWORD)]

    token = HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        raise ValueError("could not read process token identity")
    try:
        size = DWORD(0)
        # First call requests the required token-info buffer size.
        adv.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not 16 <= size.value <= 4096:
            raise ValueError("unexpected token-user structure size")
        buffer = ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise ValueError("could not read process token user")
        process_sid = ctypes.cast(buffer, ctypes.POINTER(SID_AND_ATTRIBUTES)).contents.sid
        if not process_sid:
            raise ValueError("process token has no SID")

        owner_sid, dacl, descriptor = PVOID(), PVOID(), PVOID()
        # SE_FILE_OBJECT=1; OWNER_SECURITY_INFORMATION=1; DACL_SECURITY_INFORMATION=4.
        result = adv.GetNamedSecurityInfoW(
            str(path), 1, 0x00000005, ctypes.byref(owner_sid),
            None, ctypes.byref(dacl), None, ctypes.byref(descriptor),
        )
        if result != 0:
            raise ValueError("file owner/DACL inspection failed")
        try:
            if not owner_sid or not descriptor:
                raise ValueError("file has no observed owner SID")
            return bool(adv.EqualSid(process_sid, owner_sid)), bool(dacl)
        finally:
            if descriptor:
                kernel.LocalFree(descriptor)
    finally:
        kernel.CloseHandle(token)


def inspect_file(label: str, filename: str) -> dict:
    if label not in FILE_TYPES or not isinstance(filename, str) or not filename.strip():
        raise ValueError("unknown inspection target type")
    path = Path(filename).expanduser().absolute()
    # No credential, path, username or SID is included in the response.
    base = {
        "kind": label, "exists": False, "regularFile": False,
        "ownerMatchesCurrentProcess": False,
        "singleLink": False, "filePermissionBitsPrivate": False,
        "parentDirectoryPrivate": False, "windowsDaclPresent": False,
        "candidateFilePrivateByPosixBits": False,
        "effectiveWindowsAclPrivacyVerified": False,
        "tamperProofStoreVerified": False,
        "contentRead": False, "changesMade": False,
    }
    try:
        metadata = path.lstat()
        parent = path.parent.lstat()
    except (FileNotFoundError, NotADirectoryError):
        return base
    base["exists"] = True
    if not stat.S_ISREG(metadata.st_mode) or not stat.S_ISDIR(parent.st_mode):
        return base
    if path.parent.is_symlink():
        return base
    if not 0 < metadata.st_size <= MAX_SIZE[label]:
        return base
    base["regularFile"] = True
    base["singleLink"] = metadata.st_nlink == 1
    if os.name == "posix":
        uid = os.geteuid()
        same_user = metadata.st_uid == uid
        parent_private = (parent.st_uid == uid and (stat.S_IMODE(parent.st_mode) & 0o077) == 0)
        file_private = (stat.S_IMODE(metadata.st_mode) & 0o077) == 0
        base["ownerMatchesCurrentProcess"] = same_user
        base["parentDirectoryPrivate"] = parent_private
        base["filePermissionBitsPrivate"] = file_private
        base["candidateFilePrivateByPosixBits"] = (
            same_user and parent_private and file_private and base["singleLink"]
        )
    elif os.name == "nt":
        same_user, dacl_present = _windows_identity_and_owner(path)
        base["ownerMatchesCurrentProcess"] = same_user
        base["windowsDaclPresent"] = dacl_present
        # We have NOT computed effective rights across inherited ACEs/groups.
        # Don't turn ownership or a non-null DACL into a "private file" claim.
    return base


def inspect(*, token_file: str | None = None, ledger_file: str | None = None) -> dict:
    if not token_file and not ledger_file:
        raise ValueError("supply at least one local file for inspection")
    if any(v is not None and (not isinstance(v, str) or not v.strip())
           for v in (token_file, ledger_file)):
        raise ValueError("invalid local file arguments")
    records = []
    if token_file:
        records.append(inspect_file("token", token_file))
    if ledger_file:
        records.append(inspect_file("ledger", ledger_file))
    return {
        "schemaVersion": SCHEMA,
        "report": "local_read_only_operator_observations",
        "platform": "windows" if os.name == "nt" else ("posix" if os.name == "posix" else "unknown"),
        "processIdentityObserved": os.name in ("nt", "posix"),
        "authenticatedHttpClient": False,
        "files": records,
        "allCandidateFilesPrivateByPosixBits": (
            os.name == "posix" and all(x["candidateFilePrivateByPosixBits"] for x in records)
        ),
        "windowsEffectiveAclRightsCalculated": False,
        "servicePrivilegeBoundaryVerified": False,
        "serviceSideStoreProtected": False,
        "httpExecutionAllowed": False,
        "publishingAuthorized": False,
        "contentRead": False,
        "noFilesWritten": True,
        "enabledCapabilities": list(CAPABILITIES),
        "notProven": list(DENIED),
        "note": ("File ownership and mode/DACL observation only. Windows DACL "
                 "presence does not mean effective rights are private. POSIX "
                 "mode bits do not prevent a privileged process from changing "
                 "the state. Neither authenticates a remote or local HTTP caller."),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read-only EVIE R24 token/ledger ownership inspector")
    sub = p.add_subparsers(dest="command", required=True)
    entry = sub.add_parser("inspect", help="inspect ownership/access indicators; read no secrets")
    entry.add_argument("--token-file")
    entry.add_argument("--ledger-file")
    args = p.parse_args(argv)
    try:
        report = inspect(token_file=args.token_file, ledger_file=args.ledger_file)
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, OSError, TypeError):
        print(json.dumps({
            "schemaVersion": SCHEMA, "report": "inspection_rejected",
            "httpExecutionAllowed": False,
            "serviceSideStoreProtected": False, "noFilesWritten": True,
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
