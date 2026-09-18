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
from app.rag.llm import LLM


def _default_rows(topic: str) -> List[Dict[str, Any]]:
    # 9-item placeholder set (you can pass real tools/products via constraints["items"])
    base = (topic or "Your Niche").strip()
    rows: List[Dict[str, Any]] = []
    for i in range(1, 10):
        rows.append(
            {
                "rank": i,
                "name": f"{base} Tool {i}",
                "best_for": ["beginner", "operator", "pro"][(i - 1) % 3],
                "price": ["free", "$", "$$"][i % 3],
                "rating": round(4.0 + ((i % 5) * 0.1), 1),
                "pros": "Fast, clear, practical.",
                "cons": "Requires setup; review before purchase.",
                "affiliate_link": "YOUR_AFFILIATE_LINK_HERE",
            }
        )
    return rows


def _md_table(rows: List[Dict[str, Any]], title: str) -> str:
    lines = []
    lines.append(f"# {title}\n")
    lines.append("Alignment: 369 • Φ • Fib\n")
    lines.append("| # | Tool | Best for | Price | Rating | Pros | Cons | Link |")
    lines.append("|---:|---|---|---|---:|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r.get('rank','')} | {r.get('name','')} | {r.get('best_for','')} | {r.get('price','')} | {r.get('rating','')} | {r.get('pros','')} | {r.get('cons','')} | {r.get('affiliate_link','')} |"
        )
    lines.append("\n")
    lines.append("## Disclosure\n")
    lines.append(
        "This page may contain affiliate links. If you use them, I may earn a commission at no extra cost to you. "
        "Always verify details and suitability before purchasing.\n"
    )
    return "\n".join(lines)


def _best_for_matrix(rows: List[Dict[str, Any]]) -> str:
    # 3 personas × 3 picks = 9 cells
    personas = ["beginner", "operator", "pro"]
    buckets = {p: [] for p in personas}
    for r in rows:
        p = str(r.get("best_for", "beginner")).lower().strip()
        if p not in buckets:
            p = "beginner"
        buckets[p].append(r)
    # ensure at least 3 each (pad)
    for p in personas:
        while len(buckets[p]) < 3:
            buckets[p].append({"name": f"{p.title()} Pick (TBD)", "affiliate_link": "YOUR_AFFILIATE_LINK_HERE"})
        buckets[p] = buckets[p][:3]

    lines = []
    lines.append("# Best-For Matrix (3×3)\n")
    lines.append("Alignment: 369 • Φ • Fib\n")
    lines.append("| Persona | Pick 1 | Pick 2 | Pick 3 |")
    lines.append("|---|---|---|---|")
    for p in personas:
        a, b, c = buckets[p]
        lines.append(
            f"| {p} | {a.get('name','')} | {b.get('name','')} | {c.get('name','')} |"
        )
    lines.append("\n")
    return "\n".join(lines)


class AffiliateTablesGeneratorModule:
    """Programmatic affiliate tables (local-first).

    Produces:
      - comparison_table.md (9-row table)
      - best_for_matrix.md (3x3)
      - items.csv (for programmatic pages)
      - schema_snippet.json (template for structured data / custom use)
    """

    name = "affiliate_tables_generator"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "affiliate_tables" / key
        out_root.mkdir(parents=True, exist_ok=True)

        items = constraints.get("items")
        rows: List[Dict[str, Any]]
        if isinstance(items, list) and items:
            # normalize ranks
            rows = []
            for i, it in enumerate(items, start=1):
                if isinstance(it, dict):
                    it2 = dict(it)
                    it2.setdefault("rank", i)
                    it2.setdefault("affiliate_link", "YOUR_AFFILIATE_LINK_HERE")
                    rows.append(it2)
            if not rows:
                rows = _default_rows(topic)
        else:
            rows = _default_rows(topic)

        # Optional LLM enhancement: propose a better title + hooks
        llm = LLM.from_settings()
        hook = llm.chat(
            [
                {
                    "role": "user",
                    "content": (
                        f"Write 3 short hook lines (<=12 words each) for an affiliate comparison page.\n"
                        f"Topic: {topic}\n"
                        "Constraints: no hype, no guaranteed outcomes, clear and ethical.\n"
                        "Structure: 3 lines, aligned to 369."
                    ),
                }
            ]
        )
        hooks_md = "# Hooks (3)\n\n" + hook + "\n"
        write_text(out_root / "hooks.md", hooks_md)

        # Tables
        comparison_md = _md_table(rows, f"Comparison Table — {topic}")
        write_text(out_root / "comparison_table.md", comparison_md)

        matrix_md = _best_for_matrix(rows)
        write_text(out_root / "best_for_matrix.md", matrix_md)

        # CSV export
        csv_path = out_root / "items.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["rank", "name", "best_for", "price", "rating", "pros", "cons", "affiliate_link"],
            )
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in w.fieldnames})

        # Schema snippet (template)
        schema = {
            "type": "ItemList",
            "name": f"{topic} — Top Tools",
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "numberOfItems": len(rows),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": r.get("rank", i + 1),
                    "name": r.get("name", ""),
                    "url": r.get("affiliate_link", ""),
                }
                for i, r in enumerate(rows)
            ],
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "note": "Template only; verify schema and compliance for your use case.",
        }
        (out_root / "schema_snippet.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")

        readme = (
            "# Affiliate Tables Pack\n\n"
            "This folder contains programmatic affiliate table templates.\n\n"
            "- comparison_table.md: 9-row comparison table\n"
            "- best_for_matrix.md: 3×3 persona matrix\n"
            "- items.csv: feed for programmatic pages\n"
            "- hooks.md: 3 hook lines (LLM optional)\n"
            "- schema_snippet.json: structured data template\n\n"
            "Alignment: 369 • Φ • Fib\n"
        )
        write_text(out_root / "README.md", readme)

        artifacts = [
            str(out_root / "comparison_table.md"),
            str(out_root / "best_for_matrix.md"),
            str(csv_path),
            str(out_root / "hooks.md"),
            str(out_root / "schema_snippet.json"),
            str(out_root / "README.md"),
        ]
        return ModuleResult(artifact_paths=artifacts, metadata={"out_root": str(out_root), "count": len(rows)})
