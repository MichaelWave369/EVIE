"""Public EVIE nested Shelf privacy and factual contract tests."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "shelf" / "public_nested_catalog.json"

def test_shelf_complete_sanitized_and_unique():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert data["schemaVersion"] == "evie.shelf.public-nested/1"
    assert data["source"]["totalCards"] == 159
    assert len(data["cards"]) == 159
    assert len(data["packs"]) == 9
    ids = [card["id"] for card in data["cards"]]
    assert len(set(ids)) == 159
    assert len({card["cardClass"] for card in data["cards"]}) == 7
    assert all(card["packId"] in {p["id"] for p in data["packs"]} for card in data["cards"])
    assert all(card["status"] in ("catalog_only", "bounded_adapter") for card in data["cards"])
    assert [c["id"] for c in data["cards"] if c["status"] == "bounded_adapter"] == ["shard_floor_plan_generator"]

def test_public_snapshot_excludes_commercial_personal_and_private_fields():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    sensitive = {"price_usd", "revenue_covenant", "author", "api_key",
                 "secret", "art_direction", "env", "credentials", "wallet"}
    for card in data["cards"]:
        assert not sensitive.intersection(card)
    for pack in data["packs"]:
        assert not sensitive.intersection(pack)
    assert data["source"]["sha256"] == "efe80d7172edce3db026b5160c2fa9bd41468c16b083b3d747ce96de1b485f35"

def test_architecture_audited_adapter_matches_public_card():
    legacy = json.loads((ROOT/"app"/"shelf"/"architecture_cards.json").read_text(encoding="utf-8"))
    public = json.loads(DATA.read_text(encoding="utf-8"))
    floor = next(c for c in public["cards"] if c["id"] == "shard_floor_plan_generator")
    verified = next(c for c in legacy["cards"] if c["card_id"] == "shard_floor_plan_generator")
    assert floor["status"] == verified["execution"]["status"] == "bounded_adapter"
    assert floor["outputs"] == verified["historical_contract"]["emits"]
    assert "floor_plan_dxf" in floor["outputs"]
