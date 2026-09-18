from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional
import datetime, json, shutil, time, logging

from app.settings import settings
from app.modules import REGISTRY
from app.export.packager import package_bundle, write_text
from app.db import queries
from app.flywheel.slug import slugify
from app.flywheel.integrity import record_and_report
from app.flywheel.stamping import stamp_artifacts
from app.flywheel.runctx import RunContext
from app.security.sandbox import validate_artifacts

log = logging.getLogger("evie.flywheel")


def _next_version(current: Optional[str]) -> str:
    # v001, v002...
    if not current:
        return "v001"
    try:
        n = int(current.lower().lstrip("v"))
        return f"v{n+1:03d}"
    except Exception:
        return "v001"

def _build_changelog(prev_version: Optional[str], new_version: str, topic: str, modules: List[str]) -> str:
    ts = datetime.datetime.utcnow().isoformat()
    header = f"## {new_version} — {ts}\n"
    if not prev_version:
        body = f"- Initial release for **{topic}**\n- Modules: {', '.join(modules)}\n"
    else:
        body = f"- Update from {prev_version} → {new_version}\n- Modules this build: {', '.join(modules)}\n"
    body += "- Alignment: 369 • Φ • Fib\n"
    return header + body + "\n"

@dataclass
class OfferResult:
    product_id: int
    sku: str
    version: str
    bundle_zip: str
    module_runs: List[Dict[str, Any]]
    gumroad_dir: str

def build_offer(
    topic: str,
    modules: List[str],
    constraints_by_module: Optional[Dict[str, Dict[str, Any]]] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    price_cents: int = 2900,
    tier: str = "core",
    tier_rules_path: Optional[str] = None,
    run_ctx: Optional[RunContext] = None,
) -> OfferResult:
    """Build an offer bundle from a topic + list of modules.

    v3.0 addition: optional run_ctx records a full run history (steps, timings, errors).
    """
    constraints_by_module = constraints_by_module or {}
    runs: List[Dict[str, Any]] = []
    artifact_paths: List[str] = []

    MAX_RETRIES = 2
    BACKOFF_BASE = 1.5  # seconds: 1.5, 3.0

    step_i = 0
    try:
        for mn in modules:
            m = REGISTRY.get(mn)
            if not m:
                log.warning("Module %s not in REGISTRY, skipping", mn)
                continue

            c = constraints_by_module.get(mn, {})

            # Offer QA gate can optionally inspect the artifacts generated so far
            if mn == "offer_qa_gate":
                c = {**c, "artifact_paths": list(artifact_paths)}
            if mn in {
                "platform_packs","funnel_engine","seo_engine","creative_factory","localization_engine",
                "experiment_runner","personalization_runner","membership_automation","ecosystem_template_packs",
                "affiliate_site_mode","micro_tool_generator","marketplace_listing_optimizer",
                "affiliate_tables_generator","membership_issue_generator","pod_superpack"
            } and "artifact_paths" not in c:
                c = {**c, "artifact_paths": list(artifact_paths)}

            step_id: Optional[int] = None
            if run_ctx:
                step_id = run_ctx.step_start(step_i, "module", mn, {"topic": topic, "constraints": c})

            # Retry with exponential backoff
            last_err = None
            res = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    res = m.generate(topic, c)
                    break
                except Exception as e:
                    last_err = e
                    if attempt < MAX_RETRIES:
                        wait = BACKOFF_BASE * (2 ** attempt)
                        log.warning("Module %s attempt %d failed (%s), retrying in %.1fs", mn, attempt + 1, e, wait)
                        time.sleep(wait)
                    else:
                        log.error("Module %s failed after %d attempts: %s", mn, MAX_RETRIES + 1, e)
                        raise

            chk = validate_artifacts(res.artifact_paths)
            if not chk.ok:
                raise ValueError("Artifact validation failed for %s: %s" % (mn, "; ".join(chk.problems[:10])))

            runs.append({"module": mn, "artifact_paths": res.artifact_paths, "metadata": res.metadata, "validation": chk.__dict__})
            artifact_paths.extend(res.artifact_paths)

            if run_ctx and step_id:
                run_ctx.step_done(step_id, {"module": mn, "artifact_paths": res.artifact_paths, "metadata": res.metadata, "validation": chk.__dict__})
            step_i += 1

        # Product identity (stable)
        key = slugify(topic)
        sku = f"EV369-{key}"
        existing = queries.get_product_by_sku(sku)
        prev_version = (existing or {}).get("current_version") if existing else None
        version = _next_version(prev_version)

        # Licensing + proof-of-creation stamps (local-only)
        tier_rules = None
        if tier_rules_path:
            try:
                tier_rules = json.loads(Path(tier_rules_path).read_text(encoding="utf-8"))
            except Exception:
                tier_rules = None

        stamp_step: Optional[int] = None
        if run_ctx:
            stamp_step = run_ctx.step_start(step_i, "stamping", "licensing_stamper", {"sku": sku, "version": version, "tier": tier})
        stamp_paths, stamp_meta = stamp_artifacts(
            sku=sku,
            version=version,
            artifact_paths=list(artifact_paths),
            topic_slug=key,
            tier=tier,
            tier_rules=tier_rules,
        )
        chk2 = validate_artifacts(stamp_paths)
        if not chk2.ok:
            raise ValueError("Artifact validation failed for stamping: %s" % "; ".join(chk2.problems[:10]))
        runs.append({"module": "licensing_stamper", "artifact_paths": stamp_paths, "metadata": stamp_meta, "validation": chk2.__dict__})
        artifact_paths.extend(stamp_paths)
        if run_ctx and stamp_step:
            run_ctx.step_done(stamp_step, {"artifact_paths": stamp_paths, "metadata": stamp_meta, "validation": chk2.__dict__})
        step_i += 1

        # Zip everything into one offer bundle (versioned)
        pkg_step: Optional[int] = None
        if run_ctx:
            pkg_step = run_ctx.step_start(step_i, "package", "bundle_zip", {"count": len(artifact_paths)})
        files = [Path(p) for p in artifact_paths if p]
        bundle_zip = package_bundle(f"offer_{key}_{version}", files)
        chk3 = validate_artifacts([str(bundle_zip)])
        if not chk3.ok:
            raise ValueError("Artifact validation failed for bundle zip: %s" % "; ".join(chk3.problems[:10]))
        if run_ctx and pkg_step:
            run_ctx.step_done(pkg_step, {"bundle_zip": str(bundle_zip), "validation": chk3.__dict__})
        step_i += 1

        pname = name or f"{topic} — Offer Pack"
        pdesc = description or f"Auto-generated offer bundle for: {topic}. Includes modules: {', '.join(modules)}."
        meta = {"topic": topic, "modules": modules, "runs": runs, "integrity": {}, "tier": tier}

        if not existing:
            pid = queries.create_product(
                module="bundle",
                sku=sku,
                name=pname,
                description=pdesc,
                price_cents=int(price_cents),
                status="draft",
                metadata=meta,
                product_key=key,
                current_version=version,
            )
        else:
            pid = int(existing["product_id"])
            queries.update_product(
                pid,
                name=pname,
                description=pdesc,
                price_cents=int(price_cents),
                status="draft",
                metadata=meta,
                current_version=version,
            )

        # Create version record + changelog
        change = _build_changelog(prev_version, version, topic, modules)
        queries.create_product_version(pid, version, str(bundle_zip), change, {"modules": modules, "topic": topic})
        queries.attach_asset(pid, "zip", str(bundle_zip))

        # Gumroad-ready folder (local-only): stable folder per SKU, archive version zips
        gum_dir = Path(settings.gumroad_dir) / sku
        gum_dir.mkdir(parents=True, exist_ok=True)
        archive_dir = gum_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Copy latest + archive
        shutil.copy2(bundle_zip, gum_dir / "content.zip")
        shutil.copy2(bundle_zip, archive_dir / f"content_{version}.zip")

        # Integrity + anti-duplicate report (best-effort)
        integ_step: Optional[int] = None
        if run_ctx:
            integ_step = run_ctx.step_start(step_i, "integrity", "integrity_report", {"sku": sku, "version": version})
        integrity = record_and_report(sku, version, artifact_paths + [str(bundle_zip)], gum_dir)
        if run_ctx and integ_step:
            run_ctx.step_done(integ_step, {"integrity": integrity})
        step_i += 1

        # Update product.json
        (gum_dir / "product.json").write_text(
            json.dumps(
                {
                    "sku": sku,
                    "name": pname,
                    "description": pdesc,
                    "price_cents": int(price_cents),
                    "modules": modules,
                    "topic": topic,
                    "current_version": version,
                    "tier": tier,
                    "integrity_report": integrity.get("report_path"),
                    "created_at": datetime.datetime.utcnow().isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        # Append changelog
        ch_path = gum_dir / "CHANGELOG.md"
        if not ch_path.exists():
            write_text(ch_path, f"# Changelog — {sku}\n\n")
        with ch_path.open("a", encoding="utf-8") as f:
            f.write(change)

        (gum_dir / "README.txt").write_text(
            "Upload content.zip to your storefront (Gumroad/Payhip/etc).\n"
            "archive/ keeps previous versions.\n"
            "Edit product.json to match your listing, then paste the description.\n",
            encoding="utf-8",
        )

        queries.log_audit(
            "system",
            "build_offer",
            "product",
            str(pid),
            {"sku": sku, "version": version, "zip": str(bundle_zip), "integrity_report": integrity.get("report_path")},
        )

        out = OfferResult(
            product_id=pid,
            sku=sku,
            version=version,
            bundle_zip=str(bundle_zip),
            module_runs=runs,
            gumroad_dir=str(gum_dir),
        )
        if run_ctx:
            run_ctx.done({"product_id": pid, "sku": sku, "version": version, "bundle_zip": str(bundle_zip), "gumroad_dir": str(gum_dir)})
        return out

    except Exception as e:
        if run_ctx:
            run_ctx.error(str(e))
        raise
