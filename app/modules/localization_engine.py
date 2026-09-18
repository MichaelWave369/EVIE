
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import datetime, json, re

from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text
from app.flywheel.slug import slugify

_LANGS_DEFAULT = ["es", "fr", "de"]

def _find_text_sources(artifact_paths: List[str]) -> List[Path]:
    out=[]
    for p in artifact_paths or []:
        try:
            pp = Path(p)
            if pp.exists() and pp.suffix.lower() in {".md",".txt",".json"}:
                name = pp.name.lower()
                if "listing" in name or "copy" in name or "fields" in name or "checklist" in name:
                    out.append(pp)
        except Exception:
            pass
    return out[:6]

def _translate(llm: LLM, text: str, lang: str) -> str:
    # Local model translation prompt. If LLM is disabled, we emit a scaffold.
    if llm.backend == "none":
        return f"[TRANSLATE → {lang}]\n\n{text}\n\n[/TRANSLATE]"
    system = "You are a localization assistant. Translate accurately, keep formatting, keep brand tone. Do not add medical/financial guarantees. Keep '369 • Φ • Fib' unchanged."
    user = f"Translate into {lang}. Preserve markdown and bullet structure.\n\n{text}"
    return llm.chat([{"role":"system","content":system},{"role":"user","content":user}])

class LocalizationEngineModule:
    name = "localization_engine"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        key = slugify(topic)
        out_dir = Path(settings.data_dir) / "artifacts" / "localization_engine" / key
        out_dir.mkdir(parents=True, exist_ok=True)

        langs = constraints.get("languages") or _LANGS_DEFAULT
        if isinstance(langs, str):
            langs = [x.strip() for x in langs.split(",") if x.strip()]
        langs = list(dict.fromkeys(langs))[:9]

        artifact_paths = constraints.get("artifact_paths") or []
        sources = _find_text_sources(artifact_paths)

        # If nothing to translate yet, create a base listing copy.
        base_text = ""
        if sources:
            chunks=[]
            for s in sources:
                try:
                    chunks.append(f"# Source: {s.name}\n\n{s.read_text(encoding='utf-8', errors='ignore')}\n")
                except Exception:
                    continue
            base_text = "\n---\n".join(chunks)[:18000]
        else:
            base_text = f"""# {topic} — Listing Copy (Base EN)

## 3 hooks
- Fast, practical, local-first.
- 369 • Φ • Fib aligned structure.
- Export-ready packs for marketplaces.

## 6 bullets
- Generates product artifacts locally
- Bundles into sell-ready ZIPs
- Creates platform-specific listing packs
- Produces funnel + SEO plans
- Adds support macros + QA checks
- Tracks versions + changelogs

## 9 proof points
1. Local vault + vectors
2. Modular generators
3. Repeatable packaging
4. Anti-duplicate integrity
5. A/B kit ready
6. Metrics loop compatible
7. Personalization matrix
8. Compliance language guard
9. Clear artifact manifest
"""

        llm = LLM.from_settings()
        translated_paths=[]
        for lang in langs:
            t = _translate(llm, base_text, lang)
            p = out_dir / f"listing_{lang}.md"
            write_text(p, t)
            translated_paths.append(str(p))

        meta = {
            "module": self.name,
            "languages": langs,
            "sources": [s.name for s in sources],
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }
        write_text(out_dir / "MANIFEST.json", json.dumps(meta, indent=2))
        return ModuleResult(artifact_paths=[str(out_dir/"MANIFEST.json")] + translated_paths, metadata=meta)
