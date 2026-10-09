"""EVIE R9: real local OpenBlue artifact preflight, read-only and digest-bound."""
import copy
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone

import pytest

from app.family_gate.contracts import create_proposal
from app.family_gate.openblue_preflight import (
    ARTIFACT_SCHEMA, SCHEMA, preflight_handoff, preflight_files, inspect_openblue_bytes,
)
from app.modules.openblueprint_floor_plan import build_project

NOW = datetime(2026, 10, 9, 19, 0, tzinfo=timezone.utc)


def sample():
    project = build_project("EVIE to OpenBlue contract", {
        "units": "ft", "width": 24, "depth": 16, "partition": "vertical",
        "include_door": True, "include_network": True,
    })
    artifact = {
        "schemaVersion": ARTIFACT_SCHEMA,
        "source": {"system": "EVIE", "cardId": "openblueprint_floor_plan",
                   "runId": "evie-fixture", "mode": "generated"},
        "project": project,
    }
    payload = (json.dumps(artifact) + "\n").encode()
    envelope = create_proposal(ARTIFACT_SCHEMA, "openblue",
                               hashlib.sha256(payload).hexdigest(), len(payload), now=NOW)
    return envelope, artifact, payload


def test_live_producer_contract_preflight_without_mutation():
    envelope, _, payload = sample()
    snapshot = copy.deepcopy(envelope)
    report = preflight_handoff(envelope, payload, now=NOW + timedelta(minutes=1))
    assert report["schemaVersion"] == SCHEMA
    assert report["result"] == "preflight_pass"
    assert report["walls"] == 5
    assert report["symbols"] == 2
    assert report["units"] == "ft"
    assert report["schemaMatch"] and report["digestMatch"]
    assert report["recipientAccepted"] is False
    assert report["executionAuthorized"] is False
    assert report["transportEnabled"] is False
    assert report["signedOrAuthenticated"] is False
    assert envelope == snapshot


def test_changed_bytes_digest_size_wrong_destination_and_expiry_fail():
    envelope, artifact, payload = sample()
    with pytest.raises(ValueError, match="digest mismatch"):
        preflight_handoff(envelope, payload.replace(b"evie-fixture", b"evil-fixture"),
                          now=NOW + timedelta(minutes=1))
    with pytest.raises(ValueError, match="byte length differs"):
        preflight_handoff(envelope, payload + b" ", now=NOW + timedelta(minutes=1))
    with pytest.raises(ValueError, match="target"):
        preflight_handoff({**envelope, "target": "pixelforge"}, payload, now=NOW)
    with pytest.raises(ValueError, match="expired"):
        preflight_handoff(envelope, payload, now=NOW + timedelta(hours=2))


@pytest.mark.parametrize("mutation", [
    lambda a: a["project"]["metadata"].update(units="in"),
    lambda a: a["project"]["walls"][0].update(x2=0),
    lambda a: a["project"]["walls"][0].update(x2=float("nan")),
    lambda a: a["project"]["symbols"][0].update(type="arbitrary"),
    lambda a: a["project"]["symbols"][0].update(id="evie-n"),
    lambda a: a["source"].update(mode="unaudited"),
    lambda a: a["source"].update(runId="\x00"),
    lambda a: a["project"].update(walls=[{
        "id": f"wall-{i}", "x1": 0, "y1": 0, "x2": 10,
        "y2": 0, "height": 9, "thickness": .5,
    } for i in range(401)]),
])
def test_invalid_plan_contract_fails_before_recipient(mutation):
    _, artifact, _ = sample()
    mutation(artifact)
    with pytest.raises(ValueError):
        inspect_openblue_bytes(json.dumps(artifact).encode())


def test_duplicate_json_fields_rejected():
    _, artifact, _ = sample()
    encoded = json.dumps(artifact).replace('"schemaVersion": ', '"schemaVersion": "bad", "schemaVersion": ', 1)
    with pytest.raises(ValueError, match="duplicate JSON"):
        inspect_openblue_bytes(encoded.encode())


def test_files_are_only_read_not_written(tmp_path):
    envelope, _, payload = sample()
    request = tmp_path / "envelope.json"
    plan = tmp_path / "plan.json"
    request.write_text(json.dumps(envelope), encoding="utf8")
    plan.write_bytes(payload)
    initial = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    report = preflight_files(request, plan, now=NOW + timedelta(minutes=1))
    assert report["result"] == "preflight_pass"
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == initial
    (tmp_path / "alias.json").symlink_to(plan)
    with pytest.raises(ValueError):
        preflight_files(request, tmp_path / "alias.json", now=NOW)
