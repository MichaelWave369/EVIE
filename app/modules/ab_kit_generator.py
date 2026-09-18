from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import datetime
import json

from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


def _phi_prices(price_floor_cents: int, price_ceiling_cents: int) -> List[int]:
    """Return 3 Phi-ish price points between floor and ceiling.

    The middle price is roughly the Phi split of the range (≈61.8%).
    """
    lo = max(0, int(price_floor_cents))
    hi = max(lo, int(price_ceiling_cents))
    span = hi - lo
    p_mid = lo + int(round(span * 0.618))
    p_low = lo + int(round(span * 0.382))
    p_high = hi
    # Ensure uniqueness and sorted order
    pts = sorted({p_low, p_mid, p_high})
    while len(pts) < 3:
        pts.append(pts[-1] + 100)
    return pts[:3]


class ABKitGeneratorModule:
    """A/B Kit Generator (local-only).

    Generates a 369-aligned kit you can use to test:
    - Headlines / subtitles
    - Bullets / benefit stacks
    - Thumbnail directions
    - Short hooks / CTAs
    - Price points (Phi ladder)

    Outputs:
    - JSON kit (machine-usable)
    - Markdown kit (human-usable)
    """

    name = "ab_kit_generator"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        platform = constraints.get("platform", "generic")
        audience = constraints.get("audience", "general audience")
        angle = constraints.get("angle", "practical, no-hype, step-by-step")
        price_floor = int(constraints.get("price_floor_cents", 900))
        price_ceiling = int(constraints.get("price_ceiling_cents", 9900))
        prices = _phi_prices(price_floor, price_ceiling)

        base = {
            "topic": topic,
            "platform": platform,
            "alignment": {"three": "Create/Distribute/Compound", "six": "Research/Build/Package/Convert/Deliver/Optimize", "nine": "9-asset constellation"},
            "prices_cents": prices,
            "variants": {
                "headlines": [
                    f"{topic}: The 3-Step System That Compounds",
                    f"{topic}: Build Once, Sell Forever (369 Method)",
                    f"{topic}: A Local-Only AI Engine for Passive Income",
                ],
                "subtitles": [
                    "Create • Distribute • Compound — with Vault + RAG memory",
                    "Phi-paced lessons + Fibonacci action ladders",
                    "Templates, emails, scripts, bundles — ready to publish",
                ],
                "hooks": [
                    "Turn one idea into a whole product constellation.",
                    "Stop reinventing: let your Vault do the heavy lifting.",
                    "Ship weekly without burnout using Fibonacci cadence.",
                ],
                "ctas": ["Download the bundle", "Get the starter pack", "Start the 7‑day build"],
                "thumbnail_directions": [
                    "Big title + 3 icons (Create/Distribute/Compound) + 'Local‑Only'",
                    "Before/After: messy notes → packaged bundle zip",
                    "369 grid background + '1 idea → 9 assets'",
                ],
                "description_intros": [
                    "This pack gives you a repeatable system to turn your knowledge into sellable assets.",
                    "A local-first vault + RAG engine that generates, bundles, and improves products over time.",
                    "Build a passive-income flywheel: content → offer → conversion → optimization.",
                ],
            },
            "matrix": {"headline_x_thumbnail": "Combine any headline with any thumbnail direction (3×3=9). Then pair with any CTA and hook for 27 combos."},
        }

        data = base
        raw = None
        if llm.backend != "none":
            prompt = f"""Create an A/B testing kit for a digital product listing.

Topic: {topic}
Platform: {platform}
Audience: {audience}
Angle: {angle}

Rules:
- 369 alignment: 3 headlines, 6 bullet variants, 9 hook lines (short)
- Include 3 subtitles, 3 CTAs, 3 thumbnail directions
- Include 3 price points in cents: {prices}
- Output MUST be valid JSON only (no markdown), with keys:
  topic, platform, prices_cents, variants{{headlines,subtitles,bullets,hooks,ctas,thumbnail_directions,description_intros}}, notes
"""
            raw = llm.chat([{"role": "user", "content": prompt}])
            try:
                parsed = json.loads(raw)
                # minimal sanity
                if isinstance(parsed, dict) and "variants" in parsed:
                    data = parsed
                    data.setdefault("prices_cents", prices)
                    data.setdefault("topic", topic)
                    data.setdefault("platform", platform)
            except Exception:
                # keep base, attach raw
                data = base
                data["llm_raw"] = raw

        # Render markdown
        v = data.get("variants", {})
        md = f"""# A/B Kit — {topic}

**Platform:** {platform}  
**Alignment:** 369 • Φ • Fibonacci  
**Price points (cents):** {data.get("prices_cents", prices)}

## Headlines (3)
""" + "\n".join([f"- {x}" for x in v.get("headlines", [])[:3]]) + """

## Subtitles (3)
""" + "\n".join([f"- {x}" for x in v.get("subtitles", [])[:3]]) + """

## Bullets (6)
""" + "\n".join([f"- {x}" for x in v.get("bullets", [])[:6]]) + """

## Hooks (9)
""" + "\n".join([f"- {x}" for x in v.get("hooks", [])[:9]]) + """

## CTAs (3)
""" + "\n".join([f"- {x}" for x in v.get("ctas", [])[:3]]) + """

## Thumbnail directions (3)
""" + "\n".join([f"- {x}" for x in v.get("thumbnail_directions", [])[:3]]) + """

## Description intros (3)
""" + "\n".join([f"- {x}" for x in v.get("description_intros", [])[:3]]) + """

## 27-combo test plan (Fib cadence)
- **Day 1:** Pick 3 headline×thumbnail combos (9 choices)
- **Day 2:** Swap CTAs (3 choices)
- **Day 3:** Swap description intro (3 choices)
- **Day 5:** Keep top 2 performers, refine bullets
- **Day 8:** Lock winner, update listing + archive versions
"""

        out_dir = Path(settings.data_dir) / "artifacts" / "ab_kits"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        json_path = out_dir / f"ab__{ts}.json"
        md_path = out_dir / f"ab__{ts}.md"

        write_text(json_path, json.dumps(data, indent=2))
        write_text(md_path, md)

        meta = {"topic": topic, "module": self.name, "platform": platform, "prices_cents": data.get("prices_cents", prices)}
        if raw and llm.backend != "none":
            meta["llm_used"] = True

        return ModuleResult(artifact_paths=[str(json_path), str(md_path)], metadata=meta)
