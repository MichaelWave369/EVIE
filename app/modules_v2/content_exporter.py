from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.base import BaseModule
from .base import ModuleResult


def _extract_v2_summary(meta: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(meta, dict):
        return {}
    if isinstance(meta.get("v2_summary"), dict):
        return meta.get("v2_summary") or {}
    return meta


class ContentExporter(BaseModule):
    name = "content_exporter"

    def generate(
        self,
        *,
        topic: str,
        run_folder: str,
        sku: str,
        tier: str,
        price_cents: int,
        platforms: list[str],
        constraints: dict[str, Any],
    ) -> ModuleResult:
        merged = dict(constraints or {})
        out_dir = Path(merged.get("output_dir") or run_folder)
        export_dir = out_dir / "publish_export"
        export_dir.mkdir(parents=True, exist_ok=True)

        artifacts = [str(p) for p in (merged.get("artifact_paths") or [])]
        wf_meta = merged.get("workflow_step_metadata") or {}
        dist = wf_meta.get("distribution_generator") or {}
        sales = wf_meta.get("sales_copy_generator") or {}
        product = wf_meta.get("product_packager") or {}
        newsletter = wf_meta.get("newsletter_packager") or {}
        social = wf_meta.get("social_launch_packager") or {}
        gum = wf_meta.get("gumroad_publisher") or {}
        yt = wf_meta.get("youtube_publisher") or {}
        payhip = wf_meta.get("payhip_packager") or {}
        thumb = _extract_v2_summary(wf_meta.get("thumbnail_generator") or {})
        cover = _extract_v2_summary(wf_meta.get("product_cover_generator") or {})
        social_visual = _extract_v2_summary(wf_meta.get("social_visual_generator") or {})
        preferred_final_assets = {
            "final_thumbnail": thumb.get("preferred_final_asset") or thumb.get("best_thumbnail_path") or "",
            "final_product_cover": cover.get("preferred_final_asset") or cover.get("hero_image_path") or "",
            "final_social_visual": social_visual.get("preferred_final_asset") or ((social_visual.get("social_visual_paths") or [""])[0]),
        }
        export_social_pack = bool(merged.get("export_social_pack", True))
        export_newsletter_pack = bool(merged.get("export_newsletter_pack", True))
        export_gumroad_bonus = bool(merged.get("export_gumroad_bonus", True))
        export_youtube_supporting_content = bool(merged.get("export_youtube_supporting_content", True))
        export_payhip_pack = bool(merged.get("export_payhip_pack", True))

        # Folder structure
        yt_dir = export_dir / "youtube"
        gum_dir = export_dir / "gumroad"
        newsletter_dir = export_dir / "newsletter"
        premium_dir = export_dir / "premium"
        payhip_dir = export_dir / "payhip"
        social_dir = export_dir / "social"
        logs_dir = export_dir / "logs"
        for d in [yt_dir, gum_dir, newsletter_dir, premium_dir, payhip_dir, social_dir, logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

        manifest = {
            "topic": topic,
            "export_folder": str(export_dir),
            "artifacts": artifacts,
            "metadata_keys": sorted(list(wf_meta.keys())),
            "generated_at": datetime.utcnow().isoformat(),
            "preferred_final_assets": preferred_final_assets,
        }
        manifest_path = export_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        readme_lines = [
            f"# Publish Export — {topic}",
            "",
            "## Channels",
            "- youtube/",
            "- gumroad/",
            "- newsletter/",
            "- premium/",
            "- payhip/",
            "- social/",
            "- logs/",
            "",
            "## Artifacts",
            *[f"- {p}" for p in artifacts],
        ]
        readme_path = export_dir / "README.md"
        readme_path.write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

        youtube_pack = {
            "title": dist.get("youtube_title"),
            "preferred_thumbnail": preferred_final_assets.get("final_thumbnail", ""),
            "description": dist.get("youtube_description"),
            "tags": dist.get("youtube_tags", []),
            "pinned_comment": dist.get("youtube_pinned_comment", ""),
            "cta_text": dist.get("youtube_cta", ""),
        }
        youtube_pack_path = yt_dir / "youtube_pack.json"
        youtube_pack_path.write_text(json.dumps(youtube_pack, indent=2), encoding="utf-8")

        gumroad_pack = {
            "product_name": product.get("product_name") or f"{topic} Money Pack",
            "preferred_product_cover": preferred_final_assets.get("final_product_cover", ""),
            "short_description": product.get("product_description", ""),
            "long_description": sales.get("full_description", ""),
            "bullet_benefits": sales.get("bullet_points", []),
            "price_suggestion": product.get("price_suggestion", ""),
            "bundle_contents": product.get("bundle_contents", []),
        }
        gumroad_pack_path = gum_dir / "gumroad_pack.json"
        gumroad_pack_path.write_text(json.dumps(gumroad_pack, indent=2), encoding="utf-8")

        payhip_pack = {
            "product_title": payhip.get("product_title") or gumroad_pack.get("product_name", ""),
            "short_description": payhip.get("short_description") or gumroad_pack.get("short_description", ""),
            "long_description": payhip.get("long_description") or gumroad_pack.get("long_description", ""),
            "bullet_benefits": payhip.get("bullet_benefits") or gumroad_pack.get("bullet_benefits", []),
            "price_suggestion": payhip.get("price_suggestion") or gumroad_pack.get("price_suggestion", ""),
            "category_tags": payhip.get("category_tags") or [topic.lower(), "membership", "digital product"],
            "upload_checklist": payhip.get("upload_checklist") or [
                "Create Payhip listing",
                "Paste title, descriptions, and benefits",
                "Upload bundle files",
                "Set price and publish",
            ],
            "bundle_file_references": payhip.get("bundle_file_references") or artifacts[:20],
        }
        payhip_pack_path = payhip_dir / "payhip_pack.json"
        if export_payhip_pack:
            payhip_pack_path.write_text(json.dumps(payhip_pack, indent=2), encoding="utf-8")

        newsletter_pack = {
            "newsletter_issue_draft": newsletter.get("newsletter_issue_draft") or dist.get("newsletter_draft", ""),
            "free_version_teaser": newsletter.get("free_version_teaser", ""),
            "premium_version_section": newsletter.get("premium_version_section", ""),
            "upgrade_cta": newsletter.get("upgrade_cta", ""),
            "short_promo_email": newsletter.get("short_promo_email") or dist.get("email_promo", ""),
            "cta_variants": newsletter.get("cta_variants") or dist.get("email_cta_variants", []),
            "subject_line_options": newsletter.get("subject_line_options", []),
            "beehiiv_export": newsletter.get("beehiiv_export") or {"post_body_markdown": dist.get("newsletter_draft", "")},
            "convertkit_export": newsletter.get("convertkit_export") or {"broadcast_body_text": dist.get("email_promo", "")},
        }
        newsletter_pack_path = newsletter_dir / "newsletter_pack.json"
        if export_newsletter_pack:
            newsletter_pack_path.write_text(json.dumps(newsletter_pack, indent=2), encoding="utf-8")

        premium_pack = {
            "membership_offer_name": product.get("product_name") or f"{topic} Membership Bundle",
            "bonus_asset_summary": product.get("bundle_contents") or artifacts[:5],
            "premium_asset_suggestions": [
                "study pack PDF/HTML",
                "infographic bundle",
                "slide deck with walkthrough notes",
            ],
            "upgrade_message": "Unlock premium assets and member-only implementation steps.",
        }
        premium_pack_path = premium_dir / "premium_pack.json"
        premium_pack_path.write_text(json.dumps(premium_pack, indent=2), encoding="utf-8")

        social_pack = {
            "x_launch_post": social.get("x_launch_post") or dist.get("twitter_launch_post", ""),
            "preferred_social_visual": preferred_final_assets.get("final_social_visual", ""),
            "x_thread": social.get("x_thread") or dist.get("twitter_thread", []),
            "tiktok_caption": social.get("tiktok_caption") or ((dist.get("tiktok_hooks") or [""])[0]),
            "instagram_caption": social.get("instagram_caption") or dist.get("instagram_caption", ""),
            "linkedin_post": social.get("linkedin_post") or dist.get("linkedin_post", ""),
            "cta_variants": social.get("cta_variants") or dist.get("twitter_cta_variants", []),
            "shortform_launch_snippets": social.get("shortform_launch_snippets") or dist.get("reel_short_captions", []),
        }
        social_pack_path = social_dir / "social_pack.json"
        if export_social_pack:
            social_pack_path.write_text(json.dumps(social_pack, indent=2), encoding="utf-8")

        gumroad_bonus = {
            "enabled": export_gumroad_bonus,
            "bonus_product_name": f"{topic} Member Bonus Pack",
            "bonus_description": "Companion download bundle for premium newsletter members.",
            "bundle_sources": premium_pack.get("bonus_asset_summary", []),
        }
        gumroad_bonus_path = gum_dir / "gumroad_bonus_pack.json"
        if export_gumroad_bonus:
            gumroad_bonus_path.write_text(json.dumps(gumroad_bonus, indent=2), encoding="utf-8")

        youtube_support = {
            "enabled": export_youtube_supporting_content,
            "title": dist.get("youtube_title") or f"{topic} Weekly Member Breakdown",
            "description": dist.get("youtube_description", ""),
            "pinned_comment": dist.get("youtube_pinned_comment", ""),
            "cta_text": dist.get("youtube_cta", ""),
        }
        youtube_support_path = yt_dir / "youtube_supporting_content.json"
        if export_youtube_supporting_content:
            youtube_support_path.write_text(json.dumps(youtube_support, indent=2), encoding="utf-8")

        publish_log = {
            "gumroad_status": gum.get("status", "not_run"),
            "youtube_status": yt.get("status", "not_run"),
            "gumroad_message": gum.get("message", ""),
            "youtube_message": yt.get("message", ""),
            "generated_at": datetime.utcnow().isoformat(),
        }
        publish_log_path = logs_dir / "publish_summary.json"
        publish_log_path.write_text(json.dumps(publish_log, indent=2), encoding="utf-8")

        summary = {
            "status": "exported",
            "export_folder": str(export_dir),
            "artifact_count": len(artifacts),
            "manifest_path": str(manifest_path),
            "preferred_final_assets": preferred_final_assets,
            "packs": {
                "youtube": str(youtube_pack_path),
                "youtube_supporting": str(youtube_support_path) if export_youtube_supporting_content else "",
                "gumroad": str(gumroad_pack_path),
                "gumroad_bonus": str(gumroad_bonus_path) if export_gumroad_bonus else "",
                "newsletter": str(newsletter_pack_path) if export_newsletter_pack else "",
                "premium": str(premium_pack_path),
                "payhip": str(payhip_pack_path) if export_payhip_pack else "",
                "social": str(social_pack_path) if export_social_pack else "",
                "logs": str(publish_log_path),
            },
        }
        out_artifacts = [
            str(manifest_path),
            str(readme_path),
            str(youtube_pack_path),
            str(gumroad_pack_path),
            str(premium_pack_path),
            str(publish_log_path),
        ]
        if export_newsletter_pack:
            out_artifacts.append(str(newsletter_pack_path))
        if export_social_pack:
            out_artifacts.append(str(social_pack_path))
        if export_payhip_pack:
            out_artifacts.append(str(payhip_pack_path))
        if export_gumroad_bonus:
            out_artifacts.append(str(gumroad_bonus_path))
        if export_youtube_supporting_content:
            out_artifacts.append(str(youtube_support_path))
        return ModuleResult(name=self.name, artifacts=out_artifacts, summary=summary)
