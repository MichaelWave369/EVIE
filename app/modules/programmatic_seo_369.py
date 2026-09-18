from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import datetime
import json

from app.modules.base import BaseModule, ModuleResult
from app.flywheel.slug import slugify
from app.settings import settings

# NOTE: This module is a 369-leaning extension of programmatic_seo_generator.
# It focuses on producing *many* small pages + a sitemap + internal linking hints.

def _fib(n: int) -> List[int]:
    if n <= 0:
        return []
    if n == 1:
        return [1]
    seq = [1, 2]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]

class ProgrammaticSEO369Module(BaseModule):
    name = "programmatic_seo_369"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        topic_slug = slugify(topic)

        # Controls
        max_pages = int(constraints.get("max_pages") or 369)
        max_pages = max(9, min(369, max_pages))
        seed_terms = constraints.get("seed_terms") or []
        if isinstance(seed_terms, str):
            seed_terms = [s.strip() for s in seed_terms.split(",") if s.strip()]
        if not seed_terms:
            # simple local seeds derived from topic tokens (no web)
            toks = [t for t in topic.replace("—", " ").replace("-", " ").split() if len(t) >= 4]
            seed_terms = list(dict.fromkeys([t.lower() for t in toks]))[:21] or [topic.lower()]

        # Output structure
        out_root = Path(settings.data_dir) / "artifacts" / "programmatic_seo_369" / topic_slug
        pages_dir = out_root / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        # Page template uses Phi-ish proportions: 3 sections (hook / value / CTA)
        # and 6 bullets total (2 per section), with 9 internal-link anchors.
        fib = _fib(12)

        rows = []
        for i in range(1, max_pages + 1):
            term = seed_terms[(i - 1) % len(seed_terms)]
            lane = "Pillar" if i <= (max_pages * 0.382) else ("Cluster" if i <= (max_pages * 0.618) else "Leaf")
            # 3/6/9 rhythm
            phase = 1 if i % 9 in (1,2,3) else (2 if i % 9 in (4,5,6) else 3)

            slug = slugify(f"{topic} {term} {i:03d}")
            title = f"{topic}: {term.title()} — Guide {i:03d}"
            filename = f"{i:03d}_{slug}.md"
            url = f"/seo/{topic_slug}/{filename.replace('.md','')}/"
            rows.append({
                "index": i,
                "term": term,
                "lane": lane,
                "phase_369": phase,
                "title": title,
                "slug": slug,
                "filename": filename,
                "url": url,
            })

        # Internal links: choose 9 anchors for each page
        def link_targets(i: int) -> List[int]:
            # pick indices based on Fibonacci hops
            targets = []
            for hop in fib[:9]:
                j = i + hop
                if j <= max_pages:
                    targets.append(j)
            # back-links
            for hop in fib[:9]:
                j = i - hop
                if j >= 1:
                    targets.append(j)
            # dedupe, keep first 9
            out = []
            for t in targets:
                if t not in out and t != i:
                    out.append(t)
                if len(out) >= 9:
                    break
            return out

        artifacts: List[str] = []

        for r in rows:
            i = int(r["index"])
            targets = link_targets(i)
            links = []
            for t in targets:
                tr = rows[t-1]
                links.append(f"- [{tr['title']}]({tr['filename']})")
            body = f"""# {r['title']}

**Lane:** {r['lane']}  
**369 Phase:** {r['phase_369']}  
**Seed Term:** {r['term']}

## 1) Hook (3 lines)
- What people want when they search **{r['term']}** in the context of **{topic}**  
- The fastest path to a win (no fluff)  
- A single next step you can do today  

## 2) Value (6 bullets)
- Key idea #1 (simple definition + example)  
- Key idea #2 (common pitfall + fix)  
- Quick checklist (2 items)  
- Mini framework (3 steps)  
- Metrics to track (1–3)  
- Safety / consent note (local-first, you control the data)  

## 3) CTA (Φ-shaped)
- Free: grab a lead magnet snippet  
- Core: get the workbook / vault kit  
- Premium: workshop kit + replay + bundle  

## Related Pages (9)
{chr(10).join(links)}

---

*Generated locally • aligned by 369 / Φ / Fib • {datetime.datetime.utcnow().isoformat()}*
"""
            pth = pages_dir / r["filename"]
            pth.write_text(body, encoding="utf-8")
            artifacts.append(str(pth))

        # sitemap + plan
        sitemap_csv = out_root / "sitemap.csv"
        sitemap_lines = ["index,term,lane,phase_369,title,url,filename"]
        for r in rows:
            sitemap_lines.append(
                f"{r['index']},{json.dumps(r['term'])},{r['lane']},{r['phase_369']},{json.dumps(r['title'])},{r['url']},{r['filename']}"
            )
        sitemap_csv.write_text("\n".join(sitemap_lines) + "\n", encoding="utf-8")
        artifacts.append(str(sitemap_csv))

        plan_json = out_root / "plan.json"
        plan = {
            "topic": topic,
            "topic_slug": topic_slug,
            "max_pages": max_pages,
            "seed_terms": seed_terms,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "alignment": "369 • Φ • Fib",
            "notes": "Use these pages for programmatic SEO; pair with LandingFinalizer + SEOSitePublisher for a full local site.",
        }
        plan_json.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        artifacts.append(str(plan_json))

        index_md = out_root / "INDEX.md"
        index_md.write_text(
            f"# Programmatic SEO 369\n\nTopic: **{topic}**\n\nPages: **{max_pages}**\n\nSee `sitemap.csv` for URLs and `pages/` for content.\n",
            encoding="utf-8",
        )
        artifacts.append(str(index_md))

        return ModuleResult(
            artifact_paths=artifacts,
            metadata={
                "topic_slug": topic_slug,
                "pages": max_pages,
                "seed_terms_count": len(seed_terms),
                "alignment": "369 • Φ • Fib",
            },
        )
