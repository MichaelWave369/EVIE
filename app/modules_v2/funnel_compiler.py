from __future__ import annotations
from typing import Any
import os, shutil

from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json, slugify, now_iso

def _safe_copy(src: str, dst: str):
    """Copy file if it exists; ensure parent dir; never overwrite unless identical size+mtime doesn't matter."""
    if not os.path.exists(src):
        return False
    ensure_dir(os.path.dirname(dst))
    if os.path.exists(dst):
        # keep existing
        return True
    shutil.copy2(src, dst)
    return True

def _read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

class FunnelCompiler:
    """
    Funnel Compiler (local-only)

    Stitches:
      - lead magnet (md/pdf)
      - landing surfaces (html/md)
      - checkout copy + order bump + FAQ
      - onboarding emails (fib cadence)
      - upsell sequence
    into a single per-platform export folder.
    """
    name = "funnel_compiler"

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        tslug = slugify(topic)
        out_dir = os.path.join(run_folder, "artifacts", self.name, tslug)
        ensure_dir(out_dir)

        # Known source folders
        lm_dir = os.path.join(run_folder, "artifacts", "lead_magnet_funnel_builder", tslug)
        fe_dir = os.path.join(run_folder, "artifacts", "funnel_engine")
        cp_dir = os.path.join(run_folder, "artifacts", "conversion_packager")
        wk_dir = os.path.join(run_folder, "artifacts", "workshop_webinar_kit")
        pp_dir = os.path.join(run_folder, "artifacts", "platform_packs")

        manifest = {
            "module": self.name,
            "created_at": now_iso(),
            "topic": topic,
            "sku": sku,
            "tier": tier,
            "price_cents": price_cents,
            "platforms": platforms,
            "exports": {},
        }

        arts: list[str] = []

        for platform in (platforms or ["gumroad"]):
            export_root = os.path.join(out_dir, "exports", platform)
            ensure_dir(export_root)

            # Folder layout inside the platform export
            funnel_root = os.path.join(export_root, "funnel")
            listing_root = os.path.join(export_root, "listing")
            product_root = os.path.join(export_root, "product")
            ensure_dir(funnel_root); ensure_dir(listing_root); ensure_dir(product_root)

            # 1) Lead magnet
            lead_root = os.path.join(funnel_root, "lead_magnet")
            ensure_dir(lead_root)
            _safe_copy(os.path.join(lm_dir, "LEAD_MAGNET.md"), os.path.join(lead_root, "LEAD_MAGNET.md"))
            _safe_copy(os.path.join(lm_dir, "LEAD_MAGNET.pdf"), os.path.join(lead_root, "LEAD_MAGNET.pdf"))
            _safe_copy(os.path.join(lm_dir, "FUNNEL_MAP.md"), os.path.join(lead_root, "FUNNEL_MAP.md"))

            # 2) Landing surfaces
            landing_root = os.path.join(funnel_root, "landing")
            ensure_dir(landing_root)
            _safe_copy(os.path.join(lm_dir, "LANDING_PAGE.html"), os.path.join(landing_root, "LANDING_PAGE.html"))
            # Final landing surface (with SKU/price/proof injection)
            lf_dir = os.path.join(run_folder, "artifacts", "landing_finalizer", tslug)
            _safe_copy(os.path.join(lf_dir, "FINAL_LANDING_PAGE.html"), os.path.join(landing_root, "FINAL_LANDING_PAGE.html"))
            _safe_copy(os.path.join(lf_dir, "FINAL_LANDING_PAGE.md"), os.path.join(landing_root, "FINAL_LANDING_PAGE.md"))
            _safe_copy(os.path.join(fe_dir, "LANDING_PAGE.md"), os.path.join(landing_root, "LANDING_PAGE.md"))

            # 3) Checkout + FAQ + order bump
            checkout_root = os.path.join(funnel_root, "checkout")
            ensure_dir(checkout_root)
            _safe_copy(os.path.join(fe_dir, "ORDER_BUMP.md"), os.path.join(checkout_root, "ORDER_BUMP.md"))
            _safe_copy(os.path.join(cp_dir, "FAQ.md"), os.path.join(checkout_root, "FAQ.md"))
            _safe_copy(os.path.join(cp_dir, "SUPPORT_MACROS.md"), os.path.join(checkout_root, "SUPPORT_MACROS.md"))

            checkout_compiled = f"""# Checkout Copy — {topic}

**SKU:** {sku}  
**Tier:** {tier}  
**Price:** ${price_cents/100:.2f}  

## What they get (Φ split)
- Core value (0.618): the main kit + quickstart path
- Bonus value (0.382): templates, checklists, and support macros

## Order Bump (copy/paste)
{_read_text(os.path.join(fe_dir, "ORDER_BUMP.md"))}

## FAQ (copy/paste)
{_read_text(os.path.join(cp_dir, "FAQ.md"))}

## Support Macros (internal)
{_read_text(os.path.join(cp_dir, "SUPPORT_MACROS.md"))}
"""
            checkout_compiled_path = os.path.join(checkout_root, "CHECKOUT_COPY_COMPILED.md")
            write_text(checkout_compiled_path, checkout_compiled)
            arts.append(checkout_compiled_path)

            # 4) Onboarding emails (merge)
            onboard_root = os.path.join(funnel_root, "onboarding")
            ensure_dir(onboard_root)
            _safe_copy(os.path.join(cp_dir, "EMAIL_SEQUENCE.md"), os.path.join(onboard_root, "EMAIL_SEQUENCE.md"))
            _safe_copy(os.path.join(lm_dir, "EMAIL_DRIP.md"), os.path.join(onboard_root, "EMAIL_DRIP.md"))
            if os.path.exists(wk_dir):
                _safe_copy(os.path.join(wk_dir, "FOLLOWUP_EMAILS.md"), os.path.join(onboard_root, "WORKSHOP_FOLLOWUP_EMAILS.md"))

            onboarding_compiled = f"""# Onboarding Emails — {topic} (Fib)

This file merges:
- ConversionPackager EMAIL_SEQUENCE (post-purchase)
- LeadMagnet EMAIL_DRIP (free → paid)
- Optional workshop follow-up sequence

---

## A) Free → Paid (Lead Magnet)
{_read_text(os.path.join(lm_dir, "EMAIL_DRIP.md"))}

---

## B) Post-Purchase Onboarding
{_read_text(os.path.join(cp_dir, "EMAIL_SEQUENCE.md"))}

---

## C) Workshop Follow-ups (optional)
{_read_text(os.path.join(wk_dir, "FOLLOWUP_EMAILS.md"))}
"""
            onboarding_compiled_path = os.path.join(onboard_root, "ONBOARDING_EMAILS_COMPILED.md")
            write_text(onboarding_compiled_path, onboarding_compiled)
            arts.append(onboarding_compiled_path)

            # 5) Upsell sequence
            upsell_root = os.path.join(funnel_root, "upsell")
            ensure_dir(upsell_root)
            _safe_copy(os.path.join(lm_dir, "UPSELL_PAGE.md"), os.path.join(upsell_root, "UPSELL_PAGE.md"))
            _safe_copy(os.path.join(fe_dir, "UPSELL.md"), os.path.join(upsell_root, "UPSELL.md"))

            upsell_compiled = f"""# Upsell Sequence — {topic}

## Upsell Page (lead funnel)
{_read_text(os.path.join(lm_dir, "UPSELL_PAGE.md"))}

---

## Upsell Offer Notes (funnel engine)
{_read_text(os.path.join(fe_dir, "UPSELL.md"))}
"""
            upsell_compiled_path = os.path.join(upsell_root, "UPSELL_COMPILED.md")
            write_text(upsell_compiled_path, upsell_compiled)
            arts.append(upsell_compiled_path)

            # 6) Replay/workshop assets (optional)
            replay_root = os.path.join(funnel_root, "replay")
            ensure_dir(replay_root)
            if os.path.exists(wk_dir):
                _safe_copy(os.path.join(wk_dir, "REPLAY_LANDING_PAGE.md"), os.path.join(replay_root, "REPLAY_LANDING_PAGE.md"))
                _safe_copy(os.path.join(wk_dir, "SLIDE_DECK_OUTLINE.md"), os.path.join(replay_root, "SLIDE_DECK_OUTLINE.md"))
                _safe_copy(os.path.join(wk_dir, "SPEAKER_NOTES.md"), os.path.join(replay_root, "SPEAKER_NOTES.md"))
                _safe_copy(os.path.join(wk_dir, "HANDOUT.md"), os.path.join(replay_root, "HANDOUT.md"))

            # Listing pack (platform-specific)
            checklist_src = os.path.join(pp_dir, f"{platform}_CHECKLIST.md")
            fields_src = os.path.join(pp_dir, f"{platform}_FIELDS.json")
            _safe_copy(checklist_src, os.path.join(listing_root, f"{platform.upper()}_CHECKLIST.md"))
            _safe_copy(fields_src, os.path.join(listing_root, f"{platform.upper()}_FIELDS.json"))

            # Product file pointer (content.zip is created after modules run)
            write_text(os.path.join(product_root, "CONTENT_ZIP_POINTER.txt"),
                       "After the run completes, content.zip will be copied into your publish folder.\n"
                       "Location: data/publish/<platform>/<SKU>/content.zip\n")

            # Export README
            readme = f"""# Funnel Export — {platform.upper()}

This folder is your **single export surface** for {platform}.

## What to do
1) Open **listing/** → copy/paste listing fields into {platform}
2) Upload **content.zip** from: `data/publish/{platform}/{sku}/content.zip`
3) Use **funnel/**:
   - lead_magnet/ for the freebie
   - landing/ for landing copy + HTML
   - checkout/ for bump + FAQ
   - onboarding/ for the email sequences
   - upsell/ for upsell copy
   - replay/ for workshop assets (optional)

## 369 / Φ / Fib alignment
- 3 pillars (clarify / package / distribute)
- 6 deliverables (lead, landing, checkout, onboarding, upsell, proof)
- 9 touchpoints (repurpose + follow-up)

Generated locally by FunnelCompiler.
"""
            readme_path = os.path.join(export_root, "README.md")
            write_text(readme_path, readme)
            arts.append(readme_path)

            manifest["exports"][platform] = {
                "export_root": export_root,
                "relative": os.path.relpath(export_root, run_folder),
            }

        manifest_path = os.path.join(out_dir, "MANIFEST.json")
        write_json(manifest_path, manifest)
        arts.append(manifest_path)

        return ModuleResult(
            name=self.name,
            artifacts=sorted(set([os.path.relpath(a, run_folder) for a in arts])),
            summary={"exports": manifest["exports"], "out_dir": os.path.relpath(out_dir, run_folder)}
        )
