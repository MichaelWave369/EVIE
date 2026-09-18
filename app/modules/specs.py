from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from app.modules import REGISTRY


@dataclass
class ModuleSpec:
    name: str
    description: str
    safety_tier: int = 0
    input_schema: Dict[str, Any] | None = None       # JSON Schema (constraints)
    example_constraints: Dict[str, Any] | None = None
    declared_outputs: List[str] | None = None        # file extensions or artifact types
    notes: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # ensure stable keys
        d["input_schema"] = d["input_schema"] or {}
        d["example_constraints"] = d["example_constraints"] or {}
        d["declared_outputs"] = d["declared_outputs"] or []
        return d


COMMON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "tone": {"type": "string", "description": "Voice/tone (e.g., friendly, direct, premium)."},
        "audience": {"type": "string", "description": "Target audience (who this is for)."},
        "format": {"type": "string", "description": "Preferred output format hint (md/pdf/docx/html)."},
        "length": {"type": "string", "description": "Length hint (short/medium/long)."},
        "language": {"type": "string", "description": "Language hint (e.g., en, es)."},
        "keywords": {"type": "array", "items": {"type": "string"}, "description": "Optional keywords."},
        "artifact_paths": {"type": "array", "items": {"type": "string"}, "description": "For modules that consume prior artifacts."},
    },
}


# Curated specs for the highest-impact lanes (safe: modules ignore unknown keys)
CURATED: Dict[str, ModuleSpec] = {
    "ebooks": ModuleSpec(
        name="ebooks",
        description="Generate an ebook-style asset (outline + chapters + export).",
        input_schema={**COMMON_SCHEMA, "properties": {**COMMON_SCHEMA["properties"],
            "chapters": {"type": "integer", "minimum": 3, "maximum": 30},
            "target_words": {"type": "integer", "minimum": 500, "maximum": 60000},
            "include_checklist": {"type": "boolean"},
        }},
        example_constraints={"tone": "clear + actionable", "audience": "beginners", "chapters": 8, "target_words": 12000, "format": "pdf"},
        declared_outputs=[".md", ".pdf", ".docx"],
    ),
    "youtube_script": ModuleSpec(
        name="youtube_script",
        description="Generate a YouTube script (hook → body → CTA) and supporting assets.",
        input_schema={**COMMON_SCHEMA, "properties": {**COMMON_SCHEMA["properties"],
            "duration_minutes": {"type": "number", "minimum": 1, "maximum": 30},
            "style": {"type": "string", "description": "e.g., documentary, vlog, educational"},
            "cta": {"type": "string", "description": "Call-to-action"},
        }},
        example_constraints={"duration_minutes": 8, "style": "educational", "tone": "energetic", "cta": "Download the free checklist"},
        declared_outputs=[".md", ".txt"],
    ),
    "leadmagnet": ModuleSpec(
        name="leadmagnet",
        description="Generate a lead magnet (PDF/Doc) and opt-in copy.",
        example_constraints={"format": "pdf", "tone": "warm", "audience": "busy professionals", "keywords": ["checklist", "templates"]},
        declared_outputs=[".pdf", ".docx", ".md"],
    ),
    "seo_site_compiler": ModuleSpec(
        name="seo_site_compiler",
        description="Compile an SEO site pack (pages + sitemap + simple theme).",
        example_constraints={"site_title": "Career Sanctuary", "pages": 12, "format": "html", "keywords": ["resume", "interview", "networking"]},
        declared_outputs=[".html", ".css", ".js", ".zip"],
    ),
    "offer_qa_gate": ModuleSpec(
        name="offer_qa_gate",
        description="QA gate that checks artifacts for completeness, duplicates, and policy guardrails.",
        example_constraints={"strict": True, "checks": ["duplicates", "missing_files", "pricing_sanity"], "artifact_paths": []},
        declared_outputs=[".json", ".md"],
    ),
    "miniapp": ModuleSpec(
        name="miniapp",
        description="Generate a simple mini-app product (local-first template).",
        example_constraints={"stack": "fastapi+streamlit", "features": ["dashboard", "export"], "format": "zip"},
        declared_outputs=[".zip"],
    ),
    "podcast_script_generator": ModuleSpec(
        name="podcast_script_generator",
        description="Generate a two-host podcast script and show notes.",
        example_constraints={"host_a": "Host A", "host_b": "Host B", "length": 20, "style": "conversational"},
        declared_outputs=[".md"],
    ),
    "presentation_generator": ModuleSpec(
        name="presentation_generator",
        description="Generate a PPTX slide deck from topic/context.",
        example_constraints={"slides": 8, "theme": "porch", "style": "educational"},
        declared_outputs=[".pptx"],
        notes="Requires Node.js in PATH for pptx rendering.",
    ),
    "infographic_generator": ModuleSpec(
        name="infographic_generator",
        description="Generate branded infographic images (PNG).",
        example_constraints={"layout": "phases", "theme": "porch", "size": "portrait"},
        declared_outputs=[".png"],
        notes="Requires Pillow.",
    ),
    "study_module": ModuleSpec(
        name="study_module",
        description="Generate flashcards, quizzes, or report outputs for study workflows.",
        example_constraints={"mode": "flashcards", "count": 20},
        declared_outputs=[".html", ".json", ".pdf"],
        notes="PDF report mode requires reportlab.",
    ),
    "audio_generator": ModuleSpec(
        name="audio_generator",
        description="Generate spoken MP3 audio from podcast scripts via ElevenLabs voices.",
        example_constraints={"script_path": "data/artifacts/podcast_scripts/example.md", "voice_a": "adam", "voice_b": "rachel"},
        declared_outputs=[".mp3", ".json"],
        notes="Requires ffmpeg, pydub, requests, and EV_ELEVENLABS_API_KEY.",
    ),
    "video_generator": ModuleSpec(
        name="video_generator",
        description="Generate cinematic MP4 videos from slides and optional audio.",
        example_constraints={"slides": ["data/artifacts/infographics/slide1.png"], "audio_path": "data/artifacts/audio/example.mp3", "orientation": "landscape"},
        declared_outputs=[".mp4"],
        notes="Requires moviepy, Pillow, and ffmpeg.",
    ),
    "hooks_generator": ModuleSpec(
        name="hooks_generator",
        description="Generate short high-attention hooks from script/topic context.",
        example_constraints={"script_path": "data/artifacts/podcast_scripts/example.md"},
        declared_outputs=[".json"],
    ),
    "product_packager": ModuleSpec(
        name="product_packager",
        description="Assemble artifact bundles into a marketable product package summary.",
        example_constraints={"artifact_paths": ["data/artifacts/..."]},
        declared_outputs=[".json"],
    ),
    "sales_copy_generator": ModuleSpec(
        name="sales_copy_generator",
        description="Generate headline, bullets, CTA, and product sales description.",
        example_constraints={"topic": "Wellness reset", "product_name": "Wellness Money Pack"},
        declared_outputs=[".json"],
    ),
    "distribution_generator": ModuleSpec(
        name="distribution_generator",
        description="Generate channel-ready distribution copy for video, social, and email.",
        example_constraints={"topic": "Wellness reset"},
        declared_outputs=[".json"],
    ),
    "content_exporter": ModuleSpec(
        name="content_exporter",
        description="Organize workflow outputs into a manual publishing export folder.",
        example_constraints={"artifact_paths": ["data/artifacts/..."]},
        declared_outputs=[".json", ".md"],
    ),
    "publish_controller": ModuleSpec(
        name="publish_controller",
        description="Controls publish behavior using auto_publish and dry_run safety flags.",
        example_constraints={"auto_publish": False, "dry_run": True},
        declared_outputs=[".json"],
    ),
    "gumroad_publisher": ModuleSpec(
        name="gumroad_publisher",
        description="Attempt Gumroad publishing (or simulate) from packaged product metadata.",
        example_constraints={"auto_publish": True, "dry_run": True},
        declared_outputs=[".json"],
        notes="Requires EV_GUMROAD_ACCESS_TOKEN for non-simulated publishing.",
    ),
    "newsletter_packager": ModuleSpec(
        name="newsletter_packager",
        description="Generate newsletter issue and promo export blocks for Beehiiv/ConvertKit workflows.",
        example_constraints={"topic": "Wellness reset", "export_newsletter_pack": True},
        declared_outputs=[".json"],
    ),
    "social_launch_packager": ModuleSpec(
        name="social_launch_packager",
        description="Generate launch-ready social copy pack for X, TikTok, Instagram, and LinkedIn.",
        example_constraints={"topic": "Wellness reset", "export_social_pack": True},
        declared_outputs=[".json"],
    ),


    "thread_bomber": ModuleSpec(
        name="thread_bomber",
        description="Generate X threads and long-form distribution posts from offer metadata.",
        example_constraints={"topic": "Creator AI"},
        declared_outputs=[".json"],
    ),
    "short_form_pack": ModuleSpec(
        name="short_form_pack",
        description="Generate TikTok/Instagram/Shorts script and caption packs.",
        example_constraints={"topic": "Creator AI", "clips": 6},
        declared_outputs=[".json"],
    ),
    "competitor_dissector": ModuleSpec(
        name="competitor_dissector",
        description="Analyze competitor positioning gaps and counter-positioning angles.",
        example_constraints={"competitors": ["A", "B"]},
        declared_outputs=[".json"],
    ),
    "vault_auditor": ModuleSpec(
        name="vault_auditor",
        description="Audit vault/context quality and provide operator recommendations.",
        example_constraints={"artifact_paths": ["data/artifacts/a.md"]},
        declared_outputs=[".json"],
    ),
    "comfyui_director": ModuleSpec(
        name="comfyui_director",
        description="Advanced visual control module: bridge-first handoff with ComfyUI fallback.",
        example_constraints={"style": "cinematic", "num_images": 3},
        declared_outputs=[".json", ".png"],
        notes="Does not replace image_generator_v2; extends visual orchestration.",
    ),
    "prediction_tracker": ModuleSpec(
        name="prediction_tracker",
        description="Track market/product predictions in a local SQLite journal.",
        example_constraints={"action": "add", "prediction_text": "Demand for X will rise", "confidence": 0.68, "horizon_days": 30},
        declared_outputs=[".json", ".db"],
        notes="Local SQLite tracker; supports add/list/update actions.",
    ),
    "trend_surfer": ModuleSpec(
        name="trend_surfer",
        description="Generate strategic trend signals and optional prediction candidates.",
        example_constraints={"keywords": ["ai", "creator tools"], "create_predictions": False},
        declared_outputs=[".json"],
        notes="Prompt/heuristic intelligence, not guaranteed live market telemetry.",
    ),
    "idea_miner": ModuleSpec(
        name="idea_miner",
        description="Mine monetization ideas and suggest EVIE workflow paths.",
        example_constraints={"audience": "solopreneurs"},
        declared_outputs=[".json"],
    ),
    "sales_page_builder": ModuleSpec(
        name="sales_page_builder",
        description="Build structured sales page copy blocks for Gumroad, Payhip, and storefront usage.",
        example_constraints={"product_name": "Creator Revenue Kit", "price": "$29"},
        declared_outputs=[".md", ".json"],
    ),
    "email_sequence_builder": ModuleSpec(
        name="email_sequence_builder",
        description="Build lifecycle email sequences for manual Beehiiv/ConvertKit/MailerLite workflows.",
        example_constraints={"emails": 5, "product_name": "Creator Revenue Kit"},
        declared_outputs=[".json"],
    ),
    "cross_pollinator": ModuleSpec(
        name="cross_pollinator",
        description="Find theme intersections from vault context for new product ideas.",
        example_constraints={"vault_notes": ["note a", "note b"]},
        declared_outputs=[".json"],
    ),
    "image_generator_v2": ModuleSpec(
        name="image_generator_v2",
        description="Generate AI image variations via local ComfyUI with optional API fallback.",
        example_constraints={"topic": "Wellness reset", "style": "cinematic", "num_images": 3},
        declared_outputs=[".png", ".json"],
        notes="Uses local ComfyUI if available; can fall back to OpenAI image API when enabled.",
    ),
    "payhip_packager": ModuleSpec(
        name="payhip_packager",
        description="Generate a Payhip-ready product listing pack for manual export/publishing.",
        example_constraints={"topic": "Wellness reset", "export_payhip_pack": True},
        declared_outputs=[".json"],
    ),
    "youtube_publisher": ModuleSpec(
        name="youtube_publisher",
        description="Attempt YouTube publishing (or simulate) from distribution/video metadata.",
        example_constraints={"auto_publish": True, "dry_run": True},
        declared_outputs=[".json"],
        notes="Requires EV_YOUTUBE_ACCESS_TOKEN for non-simulated publishing.",
    ),
}


def build_specs() -> Dict[str, Dict[str, Any]]:
    specs: Dict[str, Dict[str, Any]] = {}
    for name, m in REGISTRY.items():
        if name in CURATED:
            specs[name] = CURATED[name].to_dict()
            continue

        # default
        desc = (getattr(m, "__doc__", "") or "").strip().splitlines()
        description = desc[0].strip() if desc else "Module"
        ms = ModuleSpec(
            name=name,
            description=description or "Module",
            input_schema=COMMON_SCHEMA,
            example_constraints={"tone": "clear", "format": "md"},
            declared_outputs=[],
        )
        specs[name] = ms.to_dict()
    return specs
