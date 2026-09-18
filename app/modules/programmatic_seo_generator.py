from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
import csv
import datetime
import json
import re

from app.modules.base import ModuleResult
from app.settings import settings
from app.flywheel.slug import slugify
from app.export.packager import write_text


_STOP = {
    "the","and","for","with","that","this","from","into","your","you","are",
    "how","what","when","where","why","can","will","would","should","could","about",
    "over","under","after","before","tips","guide","starter","pack","bundle","local",
}


def _split_terms(topic: str) -> List[str]:
    t = re.sub(r"[^a-zA-Z0-9 ]+", " ", (topic or "")).lower()
    toks = [w.strip() for w in t.split() if len(w.strip()) >= 3]
    seeds: List[str] = []
    for w in toks:
        if w in _STOP:
            continue
        if w not in seeds:
            seeds.append(w)
    return seeds[:9] or ["embervault"]


def _fib_days() -> List[int]:
    # Enough for 369 pages (upper bound)
    fib = [1, 2]
    while len(fib) < 20:
        fib.append(fib[-1] + fib[-2])
    return fib


def _page_patterns() -> List[str]:
    return [
        "best_{x}_for_{y}",
        "{x}_vs_{y}",
        "how_to_{verb}_{x}",
        "{x}_checklist",
        "{x}_template",
        "{x}_guide",
    ]


_VERBS = ["choose", "set_up", "improve", "start", "scale", "automate"]


def _build_title(pattern: str, x: str, y: str, verb: str) -> str:
    if pattern == "best_{x}_for_{y}":
        return f"Best {x.title()} for {y.title()} (2026 Guide)"
    if pattern == "{x}_vs_{y}":
        return f"{x.title()} vs {y.title()} — Which One Fits You?"
    if pattern == "how_to_{verb}_{x}":
        return f"How to {verb.replace('_',' ').title()} {x.title()}"
    if pattern == "{x}_checklist":
        return f"{x.title()} Checklist (3–6–9)"
    if pattern == "{x}_template":
        return f"{x.title()} Template Pack (Free Outline)"
    return f"{x.title()} Guide: Step-by-Step"


def _build_slug(pattern: str, x: str, y: str, verb: str) -> str:
    base = pattern.format(x=x, y=y, verb=verb)
    base = base.replace("_", "-")
    base = re.sub(r"[^a-z0-9\-]+", "-", base.lower())
    base = re.sub(r"-+", "-", base).strip("-")
    return base


def _pillar_from_pattern(pattern: str) -> str:
    if pattern.startswith("best") or "_vs_" in pattern:
        return "discover"
    if pattern.startswith("how_to"):
        return "learn"
    return "use"


def _render_page(
    site_name: str,
    title: str,
    keyword: str,
    pillar: str,
    slug: str,
    internal_links: List[Tuple[str, str]],
    refresh_days: int,
) -> str:
    ts = datetime.datetime.utcnow().date().isoformat()
    # 3 / 6 / 9 structure
    hook3 = [
        f"This page is part of **{site_name}** — built for local-first work.",
        f"Primary keyword: **{keyword}**.",
        "Alignment: **369 • Φ • Fib** (clarity, pacing, iteration).",
    ]
    bullets6 = [
        "Define the outcome (what 'done' looks like).",
        "Choose a simple starting kit (minimum viable setup).",
        "Add guardrails (quality + safety + versioning).",
        "Package the deliverable (files + checklist + README).",
        "Distribute with consistency (calendar + repurpose plan).",
        "Optimize using feedback (A/B tests + metrics loop).",
    ]
    qa9 = [
        "What is this for?",
        "Who is it for?",
        "What is the minimum setup?",
        "What should I avoid?",
        "What is the fastest first win?",
        "How do I package it?",
        "How do I price it?",
        "How do I measure success?",
        "How do I iterate safely?",
    ]

    lines: List[str] = []
    lines.append("---")
    lines.append(f"title: \"{title}\"")
    lines.append(f"keyword: \"{keyword}\"")
    lines.append(f"pillar: \"{pillar}\"")
    lines.append(f"slug: \"{slug}\"")
    lines.append(f"created_at: \"{ts}\"")
    lines.append(f"refresh_days: {int(refresh_days)}")
    lines.append("---\n")

    lines.append(f"# {title}\n")
    lines.append("## 3-line orientation")
    for h in hook3:
        lines.append(f"- {h}")

    lines.append("\n## 6-step checklist")
    for b in bullets6:
        lines.append(f"- {b}")

    lines.append("\n## 9 questions to answer")
    for q in qa9:
        lines.append(f"- {q}")

    lines.append("\n## Internal links")
    for t, s in internal_links:
        lines.append(f"- [{t}](./{s}.md)")

    lines.append("\n---")
    lines.append("**Disclosure:** This page is generated for planning and drafting. Verify details before publishing.")
    return "\n".join(lines) + "\n"


class ProgrammaticSEOGeneratorModule:
    name = "programmatic_seo_generator"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "programmatic_seo" / key
        pages_dir = out_root / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        site_name = str(constraints.get("site_name") or "EmberVault Evergreen")
        seed_terms = constraints.get("seed_terms")
        if isinstance(seed_terms, str):
            seed_terms = [s.strip() for s in seed_terms.split(",") if s.strip()]
        terms = list(seed_terms) if seed_terms else _split_terms(topic)

        max_pages = int(constraints.get("max_pages") or 108)
        max_pages = max(9, min(max_pages, 369))  # keep it sane by default

        patterns = _page_patterns()
        fib = _fib_days()
        now = datetime.datetime.utcnow().isoformat()

        # Build page plan
        plan: List[Dict[str, Any]] = []
        for i in range(1, max_pages + 1):
            x = terms[(i - 1) % len(terms)]
            y = terms[(i) % len(terms)] if len(terms) > 1 else "results"
            verb = _VERBS[(i - 1) % len(_VERBS)]
            pattern = patterns[(i - 1) % len(patterns)]
            pillar = _pillar_from_pattern(pattern)
            slug = _build_slug(pattern, x, y, verb)
            keyword = f"{x} {y}" if "vs" not in pattern else f"{x} vs {y}"
            title = _build_title(pattern, x, y, verb)
            refresh_days = fib[(i - 1) % len(fib)]
            plan.append(
                {
                    "i": i,
                    "title": title,
                    "slug": slug,
                    "pillar": pillar,
                    "keyword": keyword,
                    "refresh_days": refresh_days,
                }
            )

        # Internal linking: 3 links per page within same pillar
        by_pillar: Dict[str, List[Dict[str, Any]]] = {"discover": [], "learn": [], "use": []}
        for p in plan:
            by_pillar[p["pillar"]].append(p)

        def pick_links(p: Dict[str, Any]) -> List[Tuple[str, str]]:
            bucket = by_pillar.get(p["pillar"], plan)
            if not bucket:
                bucket = plan
            idx = next((j for j, it in enumerate(bucket) if it["slug"] == p["slug"]), 0)
            picks = []
            for off in (1, 2, 3):
                it = bucket[(idx + off) % len(bucket)]
                picks.append((it["title"], it["slug"]))
            return picks

        # Write pages + sitemap
        sitemap_path = out_root / "sitemap.csv"
        with sitemap_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["slug", "title", "pillar", "keyword", "refresh_days"])
            for p in plan:
                links = pick_links(p)
                md = _render_page(
                    site_name=site_name,
                    title=p["title"],
                    keyword=p["keyword"],
                    pillar=p["pillar"],
                    slug=p["slug"],
                    internal_links=links,
                    refresh_days=int(p["refresh_days"]),
                )
                write_text(pages_dir / f"{p['slug']}.md", md)
                w.writerow([p["slug"], p["title"], p["pillar"], p["keyword"], int(p["refresh_days"])])

        write_text(
            out_root / "README.md",
            "# Programmatic SEO Pages (Local)\n\n"
            f"Generated at: {now}\n\n"
            "This folder contains a batch of evergreen markdown pages you can publish as a static site or blog.\n\n"
            "**369 • Φ • Fib:**\n"
            "- 3 pillars (Discover / Learn / Use)\n"
            "- 6-step checklists\n"
            "- 9-question QA blocks\n"
            "- Fibonacci refresh-day hints\n\n"
            "Files:\n"
            "- pages/*.md\n"
            "- sitemap.csv\n",
        )

        manifest = {
            "module": self.name,
            "topic": topic,
            "created_at": now,
            "site_name": site_name,
            "max_pages": max_pages,
            "terms": terms,
            "alignment": "369 • Φ • Fib",
        }
        (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        artifacts = [
            str(out_root / "README.md"),
            str(out_root / "manifest.json"),
            str(sitemap_path),
        ]
        # Include all pages (but keep it bounded)
        for p in plan:
            artifacts.append(str(pages_dir / f"{p['slug']}.md"))

        return ModuleResult(artifact_paths=artifacts, metadata={"max_pages": max_pages, "out_root": str(out_root)})
