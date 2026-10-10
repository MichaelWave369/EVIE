"""R12 source-only workflow planner: registry provenance, no module execution, no DB writes."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.workflows.preflight import read_source, plan_workflow, reachable_flags


def plan(name, flags=None):
    w, modules, digest = read_source()
    return plan_workflow(name, workflows=w, modules=modules,
                         source_digest=digest, enabled_flags=flags)


def test_cad_flow_is_only_a_candidate_without_db_run():
    report = plan("openblueprint_concept_floor_plan")
    assert report["schemaVersion"] == "evie.workflow-preflight/1"
    assert report["summary"]["candidateModules"] == 1
    assert report["steps"][0]["name"] == "openblueprint_floor_plan"
    assert report["sourceSha256"] and len(report["sourceSha256"]) == 64
    assert report["databaseTouched"] is False
    assert report["executed"] is False
    assert report["executionAuthorized"] is False
    assert report["providerAvailabilityVerified"] is False


def test_real_nested_steps_and_optional_flags():
    original = plan("vault_to_lesson_pack")
    assert next(x for x in original["steps"] if x["name"] == "audio_generator")["decision"] == "skipped_by_default"
    enabled = plan("vault_to_lesson_pack", ["include_audio"])
    assert next(x for x in enabled["steps"] if x["name"] == "audio_generator")["decision"] == "candidate_only"
    assert next(x for x in enabled["steps"] if x["name"] == "video_generator")["decision"] == "skipped_by_default"
    large = plan("trend_to_money_publish", ["run_publish_workflow"])
    assert any(x["workflow"] == "vault_to_money_publish" for x in large["steps"])
    assert any(x["name"] == "gumroad_publisher" for x in large["steps"])
    assert large["summary"]["effectReviewCandidates"] > 0
    assert all(x["executionAuthorized"] is False for x in large["steps"])


def test_unknown_flags_rejected_and_nested_cycles_fail_closed():
    w, modules, digest = read_source()
    assert "include_audio" in reachable_flags(w, "vault_to_lesson_pack")
    with pytest.raises(ValueError):
        plan_workflow("vault_to_lesson_pack", workflows=w, modules=modules,
                      source_digest=digest, enabled_flags=["unreviewed_publish"])
    with pytest.raises(ValueError):
        plan_workflow("vault_to_lesson_pack", workflows=w, modules=modules,
                      source_digest=digest, enabled_flags=["include_audio", "include_audio"])
    synthetic = {"a": {"steps":[{"workflow":"b"}]}, "b":{"steps":[{"workflow":"a"}]}}
    with pytest.raises(ValueError, match="cycle"):
        plan_workflow("a", workflows=synthetic, modules=set(), source_digest=digest)


def test_source_only_path_does_not_import_running_modules_or_database(tmp_path):
    # Source-only planner uses stdlib JSON and text parsing, not REGISTRY module instantiation.
    from app.workflows import preflight
    assert "from app.modules import REGISTRY" not in Path(preflight.__file__).read_text()
    assert "app.db" not in Path(preflight.__file__).read_text()
    assert "create_run(" not in Path(preflight.__file__).read_text()
    before = sorted(p.name for p in tmp_path.iterdir())
    result=plan("youtube_flywheel")
    assert result["summary"]["planRows"] == 5
    assert sorted(p.name for p in tmp_path.iterdir()) == before
