"""R24 read-only POSIX/Windows operator-state and candidate permission tests."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from tools import evie_operator_state as state


def private_folder(tmp_path: Path) -> Path:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    if os.name == "posix":
        root.chmod(0o700)
    return root


def test_missing_files_are_not_pretended_to_exist(tmp_path):
    root=private_folder(tmp_path)
    report=state.inspect(token_file=str(root/"missing.token"))
    assert report["files"][0]["exists"] is False
    assert report["files"][0]["candidateFilePrivateByPosixBits"] is False
    assert report["httpExecutionAllowed"] is False
    assert report["serviceSideStoreProtected"] is False
    assert report["contentRead"] is False
    assert report["noFilesWritten"] is True
    assert not (root/"missing.token").exists()


def test_regular_files_do_not_read_secret_contents_or_expose_paths(tmp_path):
    folder=private_folder(tmp_path)
    token=folder/"token.txt"
    token.write_text("TOP_SECRET_DO_NOT_PRINT_"+("a"*64),encoding="utf-8")
    if os.name=="posix":
        token.chmod(0o600)
    raw=token.read_bytes()
    before=(token.stat().st_mtime_ns,token.stat().st_size)
    result=state.inspect(token_file=str(token))
    output=json.dumps(result)
    assert token.read_bytes()==raw
    assert before==(token.stat().st_mtime_ns,token.stat().st_size)
    assert str(token) not in output
    assert "TOP_SECRET_DO_NOT_PRINT" not in output
    assert "token.txt" not in output
    entry=result["files"][0]
    assert entry["exists"] is True
    assert entry["regularFile"] is True
    assert entry["contentRead"] is False
    assert entry["tamperProofStoreVerified"] is False
    assert result["authenticatedHttpClient"] is False
    assert result["servicePrivilegeBoundaryVerified"] is False


def test_missing_and_wrong_size_and_directories_fail_closed(tmp_path):
    folder=private_folder(tmp_path)
    too_long=folder/"oversized"
    too_long.write_bytes(b"x"*129)
    too_short=folder/"zero"
    too_short.touch()
    subdir=folder/"subdirectory"
    subdir.mkdir()
    for item in (too_long,too_short,subdir):
        record=state.inspect_file("token",str(item))
        assert record["regularFile"] is False
        assert record["candidateFilePrivateByPosixBits"] is False


def test_symlinks_and_hardlinks_cannot_be_claimed_private(tmp_path):
    folder=private_folder(tmp_path)
    target=folder/"target"
    target.write_text("simulated credential"+"a"*40)
    if os.name=="posix":
        target.chmod(0o600)
    symlink=folder/"symlink"
    try:
        symlink.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this OS")
    observed=state.inspect_file("token",str(symlink))
    assert observed["regularFile"] is False
    assert observed["candidateFilePrivateByPosixBits"] is False
    alias=folder/"link"
    try:
        os.link(target,alias)
    except (OSError, NotImplementedError):
        pytest.skip("hardlinks unavailable")
    observed=state.inspect_file("token",str(target))
    assert observed["singleLink"] is False
    assert observed["candidateFilePrivateByPosixBits"] is False


@pytest.mark.skipif(os.name!="posix",reason="Unix UID/mode-bit checks")
def test_posix_private_vs_world_readable_permissions(tmp_path):
    folder=private_folder(tmp_path)
    item=folder/"token"
    item.write_text("b"*64)
    item.chmod(0o600)
    ok=state.inspect(token_file=str(item))
    assert ok["platform"]=="posix"
    assert ok["files"][0]["ownerMatchesCurrentProcess"] is True
    assert ok["files"][0]["filePermissionBitsPrivate"] is True
    assert ok["files"][0]["parentDirectoryPrivate"] is True
    assert ok["allCandidateFilesPrivateByPosixBits"] is True
    assert ok["serviceSideStoreProtected"] is False
    item.chmod(0o644)
    bad=state.inspect(token_file=str(item))
    assert bad["allCandidateFilesPrivateByPosixBits"] is False
    assert bad["files"][0]["filePermissionBitsPrivate"] is False
    item.chmod(0o600)
    folder.chmod(0o755)
    bad=state.inspect(token_file=str(item))
    assert bad["files"][0]["parentDirectoryPrivate"] is False
    assert bad["allCandidateFilesPrivateByPosixBits"] is False


@pytest.mark.skipif(os.name!="nt",reason="Native Windows ACL/SID checks")
def test_real_windows_sid_and_dacl_observation_stays_unqualified(tmp_path):
    folder=private_folder(tmp_path)
    token=folder/"token.txt"
    token.write_text("c"*64)
    result=state.inspect(token_file=str(token))
    file=result["files"][0]
    assert result["platform"]=="windows"
    assert result["processIdentityObserved"] is True
    assert file["regularFile"] is True
    assert isinstance(file["ownerMatchesCurrentProcess"],bool)
    assert isinstance(file["windowsDaclPresent"],bool)
    assert file["effectiveWindowsAclPrivacyVerified"] is False
    assert file["candidateFilePrivateByPosixBits"] is False
    assert result["windowsEffectiveAclRightsCalculated"] is False
    assert result["serviceSideStoreProtected"] is False
    assert result["httpExecutionAllowed"] is False


def test_invalid_calls_and_unsupported_file_roles_are_denied(tmp_path,capsys):
    with pytest.raises(ValueError,match="at least one"):
        state.inspect()
    with pytest.raises(ValueError,match="unknown"):
        state.inspect_file("executables",str(tmp_path/"exe"))
    with pytest.raises(ValueError):
        state.inspect(token_file=" ")
    assert state.main(["inspect"])==1
    data=json.loads(capsys.readouterr().out)
    assert data["httpExecutionAllowed"] is False
    assert data["noFilesWritten"] is True
    with pytest.raises(SystemExit):
        state.main(["publish"])
    with pytest.raises(SystemExit):
        state.main(["inspect","--authorize-execution"])


def test_private_ledger_candidate_does_not_promote_execution(tmp_path):
    folder=private_folder(tmp_path)
    ledger=folder/"nonce-ledger.sqlite"
    ledger.write_bytes(b"SQLITE_PLACEHOLDER_FOR_FILE_METADATA_TEST")
    if os.name=="posix":
        ledger.chmod(0o600)
    output=state.inspect(ledger_file=str(ledger))
    assert output["files"][0]["kind"]=="ledger"
    assert output["files"][0]["regularFile"] is True
    assert output["serviceSideStoreProtected"] is False
    assert output["httpExecutionAllowed"] is False
    assert output["noFilesWritten"] is True
