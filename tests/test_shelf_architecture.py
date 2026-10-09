"""Recovered Sovereign Shelf architecture catalog acceptance."""
import pytest
from fastapi import HTTPException
from app.shelf.architecture import load_architecture_catalog, get_architecture_card
from app.api.routes_shelf_architecture import architecture_card
from app.modules import REGISTRY

def test_exact_11_cards_and_historical_identity():
    cat = load_architecture_catalog()
    assert cat["schemaVersion"] == "evie.shelf.architecture-catalog/1"
    assert cat["source"]["registry_version"] == "1.1.0"
    assert len(cat["cards"]) == 11
    ids = {c["card_id"] for c in cat["cards"]}
    assert len(ids) == 11
    for card in cat["cards"]:
        assert card["card_id"] == "shard_" + card["slug"]
        assert card["pack_id"] == "architecture_pack"
        assert card["flem_stage"] in ("FRAME", "LIGHT", "EMERGE", "MANIFEST")
        assert isinstance(card["historical_contract"]["requires"], list)
        assert isinstance(card["historical_contract"]["emits"], list)

def test_adapter_does_not_claim_historical_dxf_svg():
    floor = get_architecture_card("floor_plan_generator")
    assert floor["card_id"] == "shard_floor_plan_generator"
    assert floor["historical_contract"]["emits"] == ["floor_plan_dxf", "floor_plan_svg"]
    assert floor["execution"]["status"] == "bounded_adapter"
    assert floor["execution"]["producer_module"] == "openblueprint_floor_plan"
    assert "openblueprint_floor_plan" in REGISTRY
    assert not set(floor["historical_contract"]["emits"]) & set(floor["execution"]["implemented_outputs"])

def test_other_cards_are_not_falsely_claimed_runnable():
    for item in load_architecture_catalog()["cards"]:
        if item["slug"] != "floor_plan_generator":
            assert item["execution"]["status"] == "catalog_only"
            assert item["execution"]["implemented_outputs"] == []

def test_two_historical_rituals_are_archived_not_executable():
    cat = load_architecture_catalog()
    slugs = {c["slug"] for c in cat["cards"]}
    assert len(cat["rituals"]) == 2
    for ritual in cat["rituals"]:
        assert ritual["status"] == "catalog_only"
        assert set(ritual["sequence"]).issubset(slugs)

def test_lookup_is_read_only_and_unknown_card_returns_404():
    c = get_architecture_card("shard_floor_plan_generator")
    c["name"] = "changed"
    assert get_architecture_card("floor_plan_generator")["name"] == "Floor Plan Generator"
    assert get_architecture_card("../../anything") is None
    with pytest.raises(HTTPException) as exc:
        architecture_card("no-such-card")
    assert exc.value.status_code == 404
