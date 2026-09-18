from __future__ import annotations

import datetime
import importlib
from pathlib import Path
from typing import Any, Dict, List, Type

from app.modules.base import BaseModule, ModuleResult
from app.flywheel.slug import slugify
from app.settings import settings


def _make_run_folder(module_name: str, topic: str) -> Path:
    """Create a unique per-run folder to avoid artifact collisions."""
    slug = slugify(topic)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run = Path(settings.data_dir) / "runs" / module_name / f"{slug}__{ts}"
    run.mkdir(parents=True, exist_ok=True)
    return run


_ACRONYMS = {
    "seo": "SEO",
    "sku": "SKU",
    "ai": "AI",
    "pdf": "PDF",
    "kdp": "KDP",
    "qa": "QA",
    "ab": "AB",
    "cta": "CTA",
    "api": "API",
}


def _candidates_from_module(module_py: str) -> List[str]:
    parts = module_py.split("_")
    # CamelCase
    camel = "".join(p.capitalize() for p in parts if p)
    # Acronym-aware CamelCase
    acr = "".join(_ACRONYMS.get(p.lower(), p.capitalize()) for p in parts if p)
    return [camel, acr]


def _resolve_generator_class(mod: Any, preferred: str) -> Type[Any]:
    # 1) exact preferred
    if hasattr(mod, preferred):
        return getattr(mod, preferred)
    # 2) derived from module name
    for cand in _candidates_from_module(getattr(mod, "__name__", "").split(".")[-1]):
        if hasattr(mod, cand):
            return getattr(mod, cand)
    # 3) last resort: first class with a generate() method
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and hasattr(obj, "generate"):
            return obj
    raise AttributeError(f"No generator class found in {mod.__name__}. Tried {preferred} + candidates.")


def run_v2(
    module_py: str,
    class_name: str,
    *,
    topic: str,
    constraints: Dict[str, Any],
    default_platforms: List[str] | None = None,
) -> ModuleResult:
    """Adapter: execute a v2.* generator (app.modules_v2) and return a v1 ModuleResult."""
    default_platforms = default_platforms or ["gumroad", "etsy", "kdp"]

    mod = importlib.import_module(f"app.modules_v2.{module_py}")
    cls = _resolve_generator_class(mod, class_name)
    gen = cls()

    run_folder = _make_run_folder(module_py, topic)
    slug = slugify(topic)

    sku = str(constraints.get("sku") or f"EV-{slug}".upper().replace("-", ""))[:32]
    tier = str(constraints.get("tier") or "core")
    price_cents = int(constraints.get("price_cents") or 2900)

    platforms = constraints.get("platforms")
    if not isinstance(platforms, list) or not platforms:
        platforms = default_platforms

    # v2 API (keyword-only)
    res = gen.generate(
        topic=topic,
        run_folder=str(run_folder),
        sku=sku,
        tier=tier,
        price_cents=price_cents,
        platforms=platforms,
        constraints=constraints or {},
    )

    meta = {
        "v2_summary": getattr(res, "summary", {}) or {},
        "run_folder": str(run_folder),
        "adapter": "v2_wrapper",
        "generator_class": cls.__name__,
    }
    artifacts = list(getattr(res, "artifacts", []) or [])

    return ModuleResult(artifact_paths=artifacts, metadata=meta)


class V2WrappedModule(BaseModule):
    """Convenience wrapper: set module_py and class_name, inherit generate()."""

    module_py: str = ""
    class_name: str = ""
    default_platforms: List[str] = ["gumroad", "etsy", "kdp"]

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        return run_v2(
            self.module_py,
            self.class_name,
            topic=topic,
            constraints=constraints or {},
            default_platforms=self.default_platforms,
        )
