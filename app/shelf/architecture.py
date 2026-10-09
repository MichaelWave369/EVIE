"""Read-only, minimal recovery of the EVIE Sovereign Shelf Architecture Pack."""
import json
from pathlib import Path

CATALOG = Path(__file__).with_name("architecture_cards.json")

def load_architecture_catalog():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != "evie.shelf.architecture-catalog/1":
        raise ValueError("unsupported shelf catalogue version")
    return data

def get_architecture_card(slug):
    if not isinstance(slug, str) or len(slug) > 80:
        return None
    return next((item for item in load_architecture_catalog()["cards"] if slug in (item["slug"], item["card_id"])), None)
