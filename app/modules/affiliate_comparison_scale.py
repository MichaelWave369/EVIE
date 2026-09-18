
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import csv
import json
import datetime
import re

from app.modules.base import ModuleResult, BaseModule
from app.settings import settings
from app.flywheel.slug import slugify


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")


class AffiliateComparisonScaleModule(BaseModule):
    """
    Generate affiliate comparison pages at scale (local templates).
    Produces many markdown pages that can pair with Affiliate Site Mode / Programmatic SEO.

    This does NOT insert affiliate IDs automatically; it creates placeholders + disclosure reminders.
    """

    name = "affiliate_comparison_scale"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        topic_slug = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "affiliate_comparison_scale" / topic_slug
        pages_dir = out_root / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        # Seed keywords
        kws: List[str] = []
        raw = constraints.get("keywords") or constraints.get("niches") or []
        if isinstance(raw, str):
            raw = [x.strip() for x in raw.split(",") if x.strip()]
        if isinstance(raw, list):
            kws = [str(x).strip() for x in raw if str(x).strip()]
        if not kws:
            # fall back to a simple decomposition
            kws = [topic, f"{topic} tools", f"{topic} templates", f"{topic} best software"]

        max_pages = int(constraints.get("max_pages") or 36)
        # 3 families: Best / Vs / Picks (3/6/9 aligned)
        best_pages = []
        vs_pages = []
        picks_pages = []

        # Build pairs for VS pages
        pairs = []
        for i in range(len(kws)):
            for j in range(i+1, len(kws)):
                pairs.append((kws[i], kws[j]))
        if not pairs:
            pairs = [(topic, "alternatives")]

        # Limit counts
        best_n = min(max_pages // 3, len(kws))
        vs_n = min(max_pages // 3, len(pairs))
        picks_n = min(max_pages - best_n - vs_n, len(kws))

        # Templated content
        def mk_best(kw: str) -> str:
            return f"""---
type: best
topic: {topic}
keyword: {kw}
alignment: "369 • Φ • Fib"
generated_at: {datetime.datetime.utcnow().isoformat()}
---

# Best {kw} for {topic}

> Disclosure: This page may contain affiliate links. Replace placeholders with your real links.

## The 3-pillar view (369)
1) **Fit** — who is it for
2) **Function** — what it does
3) **Finish** — what you can ship

## Comparison table (9 rows)
| Option | Best for | Pros | Cons | Price |
|---|---|---|---|---|
| Tool A | … | … | … | … |
| Tool B | … | … | … | … |
| Tool C | … | … | … | … |
| Tool D | … | … | … | … |
| Tool E | … | … | … | … |
| Tool F | … | … | … | … |
| Tool G | … | … | … | … |
| Tool H | … | … | … | … |
| Tool I | … | … | … | … |

## Picks (3)
- **Top pick:** [Tool A](AFFILIATE_LINK_HERE)
- **Budget pick:** [Tool B](AFFILIATE_LINK_HERE)
- **Pro pick:** [Tool C](AFFILIATE_LINK_HERE)

## FAQ (6)
1. What is {kw}?
2. How to choose?
3. What’s best for beginners?
4. What’s best for teams?
5. What mistakes to avoid?
6. What should I buy first?

## Next steps (Fib)
1 → shortlist • 2 → trial • 3 → build • 5 → publish • 8 → optimize
"""

        def mk_vs(a: str, b: str) -> str:
            return f"""---
type: vs
topic: {topic}
a: {a}
b: {b}
alignment: "369 • Φ • Fib"
generated_at: {datetime.datetime.utcnow().isoformat()}
---

# {a} vs {b} — which is better for {topic}?

> Disclosure: This page may contain affiliate links. Replace placeholders with your real links.

## Fast answer (3)
- Choose **{a}** if: …
- Choose **{b}** if: …
- Choose neither if: …

## Deep compare (6)
1) Onboarding
2) Core features
3) Quality / reliability
4) Price
5) Best use-cases
6) Hidden gotchas

## Decision matrix (9)
| Dimension | {a} | {b} |
|---|---|---|
| Fit | … | … |
| Speed | … | … |
| Customization | … | … |
| Team | … | … |
| Integrations | … | … |
| Pricing | … | … |
| Support | … | … |
| Learning curve | … | … |
| Verdict | … | … |

## Recommended links
- [{a} link](AFFILIATE_LINK_HERE)
- [{b} link](AFFILIATE_LINK_HERE)
"""

        def mk_picks(kw: str) -> str:
            return f"""---
type: picks
topic: {topic}
keyword: {kw}
alignment: "369 • Φ • Fib"
generated_at: {datetime.datetime.utcnow().isoformat()}
---

# {kw} — the 9 best picks (quick list)

> Disclosure: This page may contain affiliate links.

1) Tool A — [link](AFFILIATE_LINK_HERE)
2) Tool B — [link](AFFILIATE_LINK_HERE)
3) Tool C — [link](AFFILIATE_LINK_HERE)
4) Tool D — [link](AFFILIATE_LINK_HERE)
5) Tool E — [link](AFFILIATE_LINK_HERE)
6) Tool F — [link](AFFILIATE_LINK_HERE)
7) Tool G — [link](AFFILIATE_LINK_HERE)
8) Tool H — [link](AFFILIATE_LINK_HERE)
9) Tool I — [link](AFFILIATE_LINK_HERE)

## Notes
- Replace tools with your real recommendations.
- Keep a consistent format so you can generate many pages and internally link them.
"""

        sitemap_rows = []
        internal = {"links": {}}

        # Write pages
        for kw in kws[:best_n]:
            slug = _slug(f"best-{kw}-for-{topic}")
            path = pages_dir / f"{slug}.md"
            path.write_text(mk_best(kw), encoding="utf-8")
            best_pages.append(str(path))
            sitemap_rows.append({"slug": slug, "type": "best", "title": f"Best {kw} for {topic}", "path": str(path)})
        for a,b in pairs[:vs_n]:
            slug = _slug(f"{a}-vs-{b}-{topic}")
            path = pages_dir / f"{slug}.md"
            path.write_text(mk_vs(a,b), encoding="utf-8")
            vs_pages.append(str(path))
            sitemap_rows.append({"slug": slug, "type": "vs", "title": f"{a} vs {b} — {topic}", "path": str(path)})
        for kw in kws[:picks_n]:
            slug = _slug(f"{kw}-picks-{topic}")
            path = pages_dir / f"{slug}.md"
            path.write_text(mk_picks(kw), encoding="utf-8")
            picks_pages.append(str(path))
            sitemap_rows.append({"slug": slug, "type": "picks", "title": f"{kw} picks — {topic}", "path": str(path)})

        # Simple internal linking: each page links to 3 others (369)
        slugs = [r["slug"] for r in sitemap_rows]
        for i, s in enumerate(slugs):
            internal["links"][s] = [slugs[(i+1) % len(slugs)], slugs[(i+2) % len(slugs)], slugs[(i+3) % len(slugs)]] if len(slugs) >= 4 else []

        sitemap_csv = out_root / "sitemap.csv"
        with sitemap_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["slug","type","title","path"])
            w.writeheader()
            for r in sitemap_rows:
                w.writerow(r)

        internal_json = out_root / "internal_links.json"
        internal_json.write_text(json.dumps(internal, indent=2), encoding="utf-8")

        manifest = out_root / "MANIFEST.json"
        manifest.write_text(json.dumps({
            "topic": topic,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "alignment": "369 • Φ • Fib",
            "counts": {"best": len(best_pages), "vs": len(vs_pages), "picks": len(picks_pages)},
            "sitemap_csv": str(sitemap_csv),
            "internal_links_json": str(internal_json),
        }, indent=2), encoding="utf-8")

        return ModuleResult(
            artifact_paths=[str(sitemap_csv), str(internal_json), str(manifest)] + best_pages[:9] + vs_pages[:3] + picks_pages[:3],
            metadata={
                "pages_dir": str(pages_dir),
                "counts": {"best": len(best_pages), "vs": len(vs_pages), "picks": len(picks_pages)},
                "alignment": "369 • Φ • Fib",
            }
        )
