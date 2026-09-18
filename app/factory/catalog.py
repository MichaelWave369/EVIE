
from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path
import csv, json, datetime

from app.settings import settings
from app.db import queries

def export_catalog() -> Dict[str, Any]:
    """Export a local catalog (JSON + CSV) for all products. No network calls."""
    out_dir = Path(settings.data_dir) / "catalog"
    out_dir.mkdir(parents=True, exist_ok=True)

    products = queries.list_products(limit=500)
    rows: List[Dict[str, Any]] = []
    for p in products:
        rows.append({
            "product_id": p.get("product_id"),
            "sku": p.get("sku"),
            "name": p.get("name"),
            "module": p.get("module"),
            "price_cents": p.get("price_cents"),
            "status": p.get("status"),
            "current_version": p.get("current_version"),
            "gumroad_dir": str(Path(settings.gumroad_dir) / (p.get("sku") or "")),
            "updated_at": p.get("updated_at"),
            "created_at": p.get("created_at"),
        })

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"catalog__{ts}.json"
    csv_path = out_dir / f"catalog__{ts}.csv"
    json_path.write_text(json.dumps({"generated_at": datetime.datetime.utcnow().isoformat(), "rows": rows}, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["product_id","sku","name","module","price_cents","status","current_version","gumroad_dir","updated_at","created_at"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    return {"ok": True, "json": str(json_path), "csv": str(csv_path), "count": len(rows)}
