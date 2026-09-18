from __future__ import annotations

from typing import Dict, Any, List, Tuple
from pathlib import Path
import datetime
import itertools
import json

from app.modules.base import BaseModule, ModuleResult
from app.flywheel.slug import slugify
from app.settings import settings
from app.db import queries


def _fib(n: int) -> List[int]:
    if n <= 0:
        return []
    if n == 1:
        return [1]
    seq = [1, 2]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]


class VariantFactoryLoopsModule(BaseModule):
    """Generate a Fibonacci-cadenced variant matrix and optionally enqueue to the local factory queue.

    Why this exists:
    - You already have many generators; variants are what compound output into revenue.
    - This module creates a controlled explosion: 3 axes → 6 combos → 9 queued builds (default).

    Constraints:
    - axes: list of {"name": str, "values": [str,...]} (defaults provided)
    - max_variants: cap (default 9)
    - enqueue: bool (default True)
    - modules: list[str] (optional; if omitted uses factory default when worker runs)
    - base_topic: optional override for the base product topic
    - priority: int (default 0)
    - price_cents / tier: optional hints for downstream modules
    """

    name = "variant_factory_loops"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        topic_slug = slugify(topic)
        out_root = Path(settings.data_dir) / "artifacts" / "variant_factory_loops" / topic_slug
        out_root.mkdir(parents=True, exist_ok=True)

        axes = constraints.get("axes")
        if not isinstance(axes, list) or not axes:
            axes = [
                {"name": "audience", "values": ["coaches", "creators", "small-business"]},
                {"name": "format", "values": ["ebook", "workbook", "vault"]},
                {"name": "tone", "values": ["calm", "direct", "mystic-tech"]},
            ]

        # sanitize axes
        clean_axes: List[Tuple[str, List[str]]] = []
        for a in axes:
            if not isinstance(a, dict):
                continue
            n = str(a.get("name") or "").strip() or "axis"
            vals = a.get("values") or []
            if isinstance(vals, str):
                vals = [v.strip() for v in vals.split(",") if v.strip()]
            vals = [str(v).strip() for v in vals if str(v).strip()]
            if vals:
                clean_axes.append((n, vals))

        if not clean_axes:
            clean_axes = [("variant", ["A", "B", "C"])]

        max_variants = int(constraints.get("max_variants") or 9)
        max_variants = max(3, min(369, max_variants))

        enqueue = constraints.get("enqueue")
        enqueue = True if enqueue is None else bool(enqueue)

        modules = constraints.get("modules")
        if isinstance(modules, str):
            modules = [m.strip() for m in modules.split(",") if m.strip()]
        if not isinstance(modules, list):
            modules = None

        base_topic = str(constraints.get("base_topic") or topic).strip()
        priority = int(constraints.get("priority") or 0)

        tier = str(constraints.get("tier") or "core")
        price_cents = int(constraints.get("price_cents") or 2900)

        # Build variants (cartesian product)
        combos = list(itertools.product(*[vals for _name, vals in clean_axes]))
        # Keep in 3/6/9 rhythm: take first N, then every other, etc. (simple deterministic)
        selected: List[Tuple[str, ...]] = []
        for c in combos:
            if len(selected) >= max_variants:
                break
            selected.append(c)

        fib = _fib(len(selected))

        variants: List[Dict[str, Any]] = []
        queue_ids: List[int] = []
        now = datetime.datetime.utcnow().isoformat()

        for idx, combo in enumerate(selected, start=1):
            labels = []
            for (axis_name, _), val in zip(clean_axes, combo):
                labels.append(f"{axis_name}:{val}")
            label_str = " | ".join(labels)
            v_topic = f"{base_topic} — {label_str} — v{idx:02d}"

            variant = {
                "index": idx,
                "topic": v_topic,
                "labels": dict(zip([n for n, _ in clean_axes], combo)),
                "fib_offset": fib[idx-1] if idx-1 < len(fib) else None,
                "tier": tier,
                "price_cents": price_cents,
            }
            variants.append(variant)

            if enqueue:
                q_constraints = {
                    "tier": tier,
                    "price_cents": price_cents,
                    "variant_labels": variant["labels"],
                    "generated_by": self.name,
                    "generated_at": now,
                }
                if modules is not None:
                    qid = queries.enqueue_queue_item(topic=v_topic, modules=modules, constraints=q_constraints, priority=priority)
                else:
                    # If modules omitted, store empty list; factory.run_next will use its default modules
                    qid = queries.enqueue_queue_item(topic=v_topic, modules=[], constraints=q_constraints, priority=priority)
                queue_ids.append(qid)

        variants_json = out_root / "variants.json"
        variants_json.write_text(json.dumps({
            "topic": topic,
            "base_topic": base_topic,
            "axes": [{"name": n, "values": v} for n, v in clean_axes],
            "max_variants": max_variants,
            "enqueue": enqueue,
            "queue_ids": queue_ids,
            "variants": variants,
            "alignment": "369 • Φ • Fib",
            "generated_at": now,
        }, indent=2), encoding="utf-8")

        artifacts = [str(variants_json)]

        return ModuleResult(
            artifact_paths=artifacts,
            metadata={
                "variants": len(variants),
                "enqueued": len(queue_ids),
                "queue_ids": queue_ids,
                "alignment": "369 • Φ • Fib",
            },
        )
