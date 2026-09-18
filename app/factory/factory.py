
from __future__ import annotations
from typing import Dict, Any, List, Optional
import datetime, json

from app.db import queries
from app.flywheel.builder import build_offer
from app.flywheel.runctx import RunContext

from app.flywheel.slug import slugify
from app.scheduler.jobs import enqueue_task


def _phi_prices(base_cents: int = 900) -> List[int]:
    # Φ-inspired ladder: entry / core / premium
    # (not a claim of mathematical optimality; just a consistent scheme)
    entry = base_cents
    core = int(base_cents * 3.22)   # ~φ^2 * 3-ish
    premium = int(core * 3.41)
    # round to nearest 100
    def r(x): return int(round(x/100.0)*100)
    return [r(entry), r(core), r(premium)]

def _default_modules() -> List[str]:
    # A compact, high-output set (you can override per queue item)
    return [
        "trend_miner",
        "offer_ladder",
        "conversion_packager",
        "repurposer",
        "calendar_generator",
        "brandkit_cover_factory",
        "terms_generator",
        "ab_kit_generator",
        "affiliate_tables_generator",
        "membership_issue_generator",
        "pod_superpack",
        "offer_qa_gate",
        # v2.x income accelerators
        "prompt_library_generator",
        "vault_generator",
        "journal_workbook_generator",
        "workshop_webinar_kit",
        "funnel_compiler",
        "landing_finalizer",
        "seo_site_compiler",
        "seo_site_publisher",
        "pricing_listing_variant_runner",
        "bundle_upsell_engine",
        "analytics_import_normalizer",
        "testimonial_collector",
        "membership_drip_calendar",
        "repurposing_scheduler",
        "collaboration_case_study_generator",
        "sku_library_compiler",
        "social_posts",
        # content lanes
        "ebooks","templates","newsletter","youtube","leadmagnet","programmatic_seo_generator","pod_pack_generator"
    ]

def seed_queue(
    focus: str,
    niches: Optional[List[str]] = None,
    top_n: int = 9,
    modules: Optional[List[str]] = None,
    constraints_by_module: Optional[Dict[str, Dict[str, Any]]] = None,
    priority: int = 0,
    schedule_fib: bool = True,
) -> Dict[str, Any]:
    """Create a 9-pack queue. Local-only.
    - If niches provided: uses them.
    - Else: derives simple keyword seeds from your last docs via the DB itself (no web).
    """
    modules = modules or _default_modules()
    constraints_by_module = constraints_by_module or {}

    # Build topic seeds
    seeds: List[str] = []
    if niches:
        for n in niches:
            if n and n.strip():
                seeds.append(n.strip())
    if not seeds:
        # pull a few recent keywords from documents (very lightweight)
        # (TrendMinerModule can be run separately; factory can operate without an LLM.)
        from app.db.schema import connect
        from collections import Counter
        con = connect()
        rows = con.execute("SELECT raw_text FROM documents ORDER BY created_at DESC LIMIT 200").fetchall()
        con.close()
        stop = set(["that","with","this","from","your","have","will","into","about","they","them","then","there","what","when","where","which","would","could","should","also","more","only","make","just","than","their","therefore","because"])
        words = []
        for r in rows:
            txt = (r["raw_text"] or "")[:4000].lower()
            toks = [w.strip(".,:;!?()[]{}<>\"'") for w in txt.split()]
            words.extend([w for w in toks if len(w) >= 5 and w.isalpha() and w not in stop])
        top = [w for w,_c in Counter(words).most_common(12)]
        seeds = top[:max(3, min(12, top_n))] or [focus]


    # Create 9 topics using 3/6/9 pattern
    topics: List[str] = []
    base_slug = slugify(focus)
    for i in range(1, top_n + 1):
        seed = seeds[(i-1) % len(seeds)]
        tier = "entry" if i <= 3 else ("core" if i <= 6 else "premium")
        topics.append(f"{focus} — {seed} ({tier}) — Pack {i:02d}")

    created_ids: List[int] = []
    prices = _phi_prices(900)
    for i, t in enumerate(topics, start=1):
        tier = "entry" if i <= 3 else ("core" if i <= 6 else "premium")
        price = prices[0] if tier=="entry" else (prices[1] if tier=="core" else prices[2])
        # Constraints can include a price hint (used by scheduler/worker)
        constraints = {
            "price_cents": price,
            "tier": tier,
            "constraints_by_module": constraints_by_module,
        }
        qid = queries.enqueue_queue_item(topic=t, modules=modules, constraints=constraints, priority=priority)
        created_ids.append(qid)

    # Optional: schedule build tasks with Fibonacci spacing
    task_ids: List[int] = []
    if schedule_fib:
        # Generate fib offsets long enough (1,2,3,5,8,13,21,34,...)
        fib = [1, 2]
        while len(fib) < len(created_ids):
            fib.append(fib[-1] + fib[-2])
        now = datetime.datetime.utcnow()
        for qid, day in zip(created_ids, fib[:len(created_ids)]):
            when = (now + datetime.timedelta(days=int(day))).replace(minute=0, second=0, microsecond=0)
            payload = {"queue_id": qid}
            task_ids.append(enqueue_task(module="factory", task_type="build_queue_item", payload=payload, schedule_at=when.isoformat()))

    return {
        "focus": focus,
        "count": len(created_ids),
        "queue_ids": created_ids,
        "task_ids": task_ids,
        "modules": modules,
        "alignment": "369 • Φ • Fib",
    }

def list_queue(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    return queries.list_queue(status=status, limit=limit)

def run_next(default_price_cents: int = 2900) -> Dict[str, Any]:
    """Claims the next queued item, builds its offer bundle, and marks it done."""
    item = queries.claim_next_queue_item()
    if not item:
        return {"ok": True, "message": "Queue empty."}

    qid = int(item["queue_id"])
    topic = item["topic"]
    modules = item.get("modules") or _default_modules()
    constraints = item.get("constraints") or {}
    price_cents = int(constraints.get("price_cents") or default_price_cents)
    constraints_by_module = constraints.get("constraints_by_module") or {}

    input_obj = {"queue_id": qid, "topic": topic, "modules": modules, "constraints": constraints}
    run_id = queries.create_run(run_type="factory", module="bundle", topic=topic, input_obj=input_obj, actor="system")
    input_obj["run_id"] = run_id
    run_ctx = RunContext(run_id=run_id, actor="system")

    try:
        tier = str(constraints.get("tier") or "core")
        tier_rules_path = constraints.get("tier_rules_path")
        res = build_offer(topic=topic, modules=modules, constraints_by_module=constraints_by_module, price_cents=price_cents, tier=tier, tier_rules_path=tier_rules_path, run_ctx=run_ctx)
        out = {
            "run_id": run_id,
            "queue_id": qid,
            "topic": topic,
            "product_id": res.product_id,
            "sku": res.sku,
            "bundle_zip": res.bundle_zip,
            "gumroad_dir": res.gumroad_dir,
            "version": res.version,
        }
        queries.finish_queue_item(qid, "done", out, None)
        return {"ok": True, **out}
    except Exception as e:
        try:
            queries.finish_run(run_id, status="error", output_obj={}, error=str(e))
        except Exception:
            pass
        queries.finish_queue_item(qid, "error", {}, str(e))
        return {"ok": False, "run_id": run_id,
            "queue_id": qid, "error": str(e), "topic": topic}
