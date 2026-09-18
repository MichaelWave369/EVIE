from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import csv
import datetime
import json

from app.modules.base import ModuleResult
from app.settings import settings
from app.flywheel.slug import slugify
from app.export.packager import write_text
from app.db import queries


def _phi_prices(base_cents: int = 900) -> List[int]:
    # Entry/Core/Premium price ladder (rounded to nearest $1)
    entry = base_cents
    core = int(round(base_cents * 3.22))
    premium = int(round(core * 3.41))
    return [entry, core, premium]


def _tier_modules(tier: str) -> List[str]:
    # A reasonable tiering; user can override in constraints
    if tier == "entry":
        return [
            "offer_ladder",
            "conversion_packager",
            "platform_packs",
            "marketplace_listing_optimizer",
        ]
    if tier == "core":
        return [
            "trend_miner",
            "offer_ladder",
            "conversion_packager",
            "funnel_engine",
            "seo_engine",
            "affiliate_tables_generator",
            "affiliate_site_mode",
            "platform_packs",
            "marketplace_listing_optimizer",
            "creative_factory",
            "programmatic_seo_generator",
        ]
    # premium
    return [
        "trend_miner",
        "offer_ladder",
        "conversion_packager",
        "funnel_engine",
        "seo_engine",
        "programmatic_seo_generator",
        "affiliate",
        "affiliate_tables_generator",
        "affiliate_site_mode",
        "membership_automation",
        "membership_issue_generator",
        "pod_pack_generator",
        "pod_superpack",
        "pod",
        "platform_packs",
        "marketplace_listing_optimizer",
        "brandkit_cover_factory",
        "creative_factory",
        "localization_engine",
        "ab_kit_generator",
        "terms_generator",
        "offer_qa_gate",
    ]


class BundleAssemblerModule:
    """Assemble a 9-SKU plan (3 angles × 3 tiers) and optionally enqueue builds.

    - Produces a bundle plan (CSV+JSON) with 9 SKUs
    - Optional: enqueue the 9 items into Product Factory queue (local DB)
    """

    name = "bundle_assembler"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "bundle_assembler" / key
        out_root.mkdir(parents=True, exist_ok=True)

        angles = constraints.get("angles") or ["Starter Kit", "Operator Kit", "Master Kit"]
        angles = [str(a).strip() for a in angles if str(a).strip()]
        angles = (angles + ["Starter Kit", "Operator Kit", "Master Kit"])[:3]

        tiers = ["entry", "core", "premium"]
        prices = _phi_prices(int(constraints.get("base_price_cents") or 900))
        price_map = {"entry": prices[0], "core": prices[1], "premium": prices[2]}

        # allow override modules per tier
        modules_by_tier = constraints.get("modules_by_tier") or {}
        def get_modules(t: str) -> List[str]:
            m = modules_by_tier.get(t)
            if isinstance(m, list) and m:
                return [str(x) for x in m]
            return _tier_modules(t)

        sku_prefix = str(constraints.get("sku_prefix") or f"EV369-{key}")
        enqueue = bool(constraints.get("enqueue_to_factory") if "enqueue_to_factory" in constraints else True)
        priority = int(constraints.get("priority") or 0)

        rows: List[Dict[str, Any]] = []
        created_queue_ids: List[int] = []

        idx = 0
        for angle in angles:
            for tier in tiers:
                idx += 1
                sku = f"{sku_prefix}-{angle.split()[0].upper()}-{tier.upper()}"
                ttopic = f"{topic} — {angle} — {tier.title()}"
                row = {
                    "index": idx,
                    "sku": sku,
                    "topic": ttopic,
                    "angle": angle,
                    "tier": tier,
                    "price_cents": price_map[tier],
                    "modules": get_modules(tier),
                }
                rows.append(row)

                if enqueue:
                    qid = queries.enqueue_queue_item(
                        topic=ttopic,
                        modules=row["modules"],
                        constraints={"price_cents": row["price_cents"], "tier": row["tier"], "constraints_by_module": constraints.get("constraints_by_module") or {}},
                        priority=priority,
                    )
                    created_queue_ids.append(qid)

        # Write CSV + JSON
        csv_path = out_root / "bundle_plan.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["index", "sku", "topic", "angle", "tier", "price_cents", "modules"])
            w.writeheader()
            for r in rows:
                rr = dict(r)
                rr["modules"] = ";".join(rr["modules"])
                w.writerow(rr)

        json_path = out_root / "bundle_plan.json"
        json_path.write_text(
            json.dumps(
                {
                    "module": self.name,
                    "topic": topic,
                    "sku_prefix": sku_prefix,
                    "angles": angles,
                    "tiers": tiers,
                    "prices": price_map,
                    "enqueue_to_factory": enqueue,
                    "queue_ids": created_queue_ids,
                    "rows": rows,
                    "created_at": datetime.datetime.utcnow().isoformat(),
                    "alignment": "369 • Φ • Fib",
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        readme = (
            "# Bundle Assembler (9 SKUs)\n\n"
            "This module creates a 9-SKU plan (3 angles × 3 tiers).\n\n"
            "Outputs:\n"
            "- bundle_plan.csv\n"
            "- bundle_plan.json\n\n"
            "If `enqueue_to_factory` is true (default), it also seeds the local Product Factory queue.\n"
            "Run builds via:\n"
            "- Dashboard → Factory → Run Next\n"
            "- or API: POST /v1/factory/run_next\n\n"
            "Alignment: 369 • Φ • Fib\n"
        )
        write_text(out_root / "README.md", readme)

        artifacts = [str(csv_path), str(json_path), str(out_root / "README.md")]
        return ModuleResult(
            artifact_paths=artifacts,
            metadata={"out_root": str(out_root), "enqueue": enqueue, "queue_ids": created_queue_ids, "count": len(rows)},
        )
