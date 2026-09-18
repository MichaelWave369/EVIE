from __future__ import annotations

from app.modules import REGISTRY


def test_notebooklm_modules_registered():
    for name in [
        "podcast_script_generator",
        "presentation_generator",
        "infographic_generator",
        "study_module",
        "audio_generator",
        "video_generator",
        "hooks_generator",
        "product_packager",
        "sales_copy_generator",
        "distribution_generator",
        "content_exporter",
        "publish_controller",
        "gumroad_publisher",
        "youtube_publisher",
        "newsletter_packager",
        "social_launch_packager",
        "payhip_packager",
        "image_generator_v2",
        "thumbnail_generator",
        "product_cover_generator",
        "social_visual_generator",
        "visual_ranker",
        "prediction_tracker",
        "trend_surfer",
        "idea_miner",
        "sales_page_builder",
        "email_sequence_builder",
        "cross_pollinator",
        "thread_bomber",
        "short_form_pack",
        "competitor_dissector",
        "vault_auditor",
        "comfyui_director",
    ]:
        assert name in REGISTRY


def test_podcast_and_study_generate_without_crash():
    podcast = REGISTRY["podcast_script_generator"]
    p_res = podcast.generate("Test Topic", {"length": 1})
    assert isinstance(p_res.artifact_paths, list)
    assert "run_folder" in p_res.metadata

    study = REGISTRY["study_module"]
    s_res = study.generate("Test Topic", {"mode": "flashcards", "count": 3})
    assert isinstance(s_res.artifact_paths, list)
    assert "v2_summary" in s_res.metadata


def test_dependency_failures_are_graceful(monkeypatch):
    from app.modules_v2.presentation_generator import PresentationGenerator
    from app.modules_v2.infographic_generator import InfographicGenerator

    monkeypatch.setattr("app.modules_v2.presentation_generator.shutil.which", lambda _cmd: None)
    pres = PresentationGenerator().generate(
        topic="Dependency Test",
        run_folder="data/runs/test/presentation",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={},
    )
    assert pres.artifacts == []
    assert "requires Node.js" in (pres.summary.get("error") or "")

    monkeypatch.setattr("app.modules_v2.infographic_generator.Image", None)
    info = InfographicGenerator().generate(
        topic="Dependency Test",
        run_folder="data/runs/test/infographic",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={},
    )
    assert info.artifacts == []
    assert "requires Pillow" in (info.summary.get("error") or "")


def test_audio_video_generate_non_crashing(monkeypatch):
    from app.modules_v2.audio_generator import AudioGenerator
    from app.modules_v2.video_generator import VideoGenerator

    # Stub dependency checks + runtime run()
    monkeypatch.setattr("app.modules_v2.audio_generator.shutil.which", lambda _cmd: "/usr/bin/ffmpeg")
    monkeypatch.setattr("app.modules_v2.audio_generator.importlib.util.find_spec", lambda _name: object())
    monkeypatch.setattr(AudioGenerator, "_get_api_key", lambda self: "key")
    monkeypatch.setattr(
        AudioGenerator,
        "run",
        lambda self, topic, constraints, context="": {
            "artifact_path": f"{constraints['output_dir']}/audio.mp3",
            "meta_path": f"{constraints['output_dir']}/audio_info.json",
        },
    )
    a = AudioGenerator().generate(
        topic="Audio Topic",
        run_folder="data/runs/test/audio",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={},
    )
    assert len(a.artifacts) == 2

    monkeypatch.setattr("app.modules_v2.video_generator.shutil.which", lambda _cmd: "/usr/bin/ffmpeg")
    monkeypatch.setattr("app.modules_v2.video_generator.importlib.util.find_spec", lambda _name: object())
    monkeypatch.setattr("app.modules_v2.video_generator.VideoClip", object())
    monkeypatch.setattr("app.modules_v2.video_generator.Image", object())
    monkeypatch.setattr(
        VideoGenerator,
        "run",
        lambda self, topic, constraints, context="": {
            "artifact_path": f"{constraints['output_dir']}/video.mp4",
        },
    )
    v = VideoGenerator().generate(
        topic="Video Topic",
        run_folder="data/runs/test/video",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={},
    )
    assert len(v.artifacts) == 1


def test_audio_video_missing_dependencies_are_graceful(monkeypatch):
    from app.modules_v2.audio_generator import AudioGenerator
    from app.modules_v2.video_generator import VideoGenerator

    monkeypatch.setattr("app.modules_v2.audio_generator.shutil.which", lambda _cmd: None)
    monkeypatch.setattr("app.modules_v2.audio_generator.importlib.util.find_spec", lambda _name: None)
    a = AudioGenerator().generate(
        topic="Audio Topic",
        run_folder="data/runs/test/audio",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={},
    )
    assert a.artifacts == []
    assert "missing dependencies" in (a.summary.get("error") or "")

    monkeypatch.setattr("app.modules_v2.video_generator.shutil.which", lambda _cmd: None)
    monkeypatch.setattr("app.modules_v2.video_generator.importlib.util.find_spec", lambda _name: None)
    monkeypatch.setattr("app.modules_v2.video_generator.VideoClip", None)
    monkeypatch.setattr("app.modules_v2.video_generator.Image", None)
    v = VideoGenerator().generate(
        topic="Video Topic",
        run_folder="data/runs/test/video",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={},
    )
    assert v.artifacts == []
    assert "missing dependencies" in (v.summary.get("error") or "")


def test_money_modules_output_expected_keys():
    from app.modules_v2.hooks_generator import HooksGenerator
    from app.modules_v2.product_packager import ProductPackager
    from app.modules_v2.sales_copy_generator import SalesCopyGenerator
    from app.modules_v2.distribution_generator import DistributionGenerator

    hooks = HooksGenerator().generate(
        topic="Topic",
        run_folder="data/runs/test/hooks",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={},
    )
    assert "hooks" in hooks.summary

    product = ProductPackager().generate(
        topic="Topic",
        run_folder="data/runs/test/product",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"artifact_paths": ["data/artifacts/a.md"]},
    )
    assert "product_name" in product.summary
    assert "bundle_contents" in product.summary

    sales = SalesCopyGenerator().generate(
        topic="Topic",
        run_folder="data/runs/test/sales",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"workflow_step_metadata": {"product_packager": product.summary}},
    )
    assert "headline" in sales.summary
    assert "call_to_action" in sales.summary

    dist = DistributionGenerator().generate(
        topic="Topic",
        run_folder="data/runs/test/dist",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"workflow_step_metadata": {"hooks_generator": hooks.summary, "product_packager": product.summary}},
    )
    assert "youtube_title" in dist.summary
    assert "twitter_thread" in dist.summary


def test_publish_modules_output_expected_keys():
    from app.modules_v2.content_exporter import ContentExporter
    from app.modules_v2.publish_controller import PublishController
    from app.modules_v2.gumroad_publisher import GumroadPublisher
    from app.modules_v2.youtube_publisher import YoutubePublisher
    from app.modules_v2.newsletter_packager import NewsletterPackager
    from app.modules_v2.social_launch_packager import SocialLaunchPackager
    from app.modules_v2.payhip_packager import PayhipPackager
    from app.modules_v2.image_generator_v2 import ImageGeneratorV2
    from app.modules_v2.thumbnail_generator import ThumbnailGenerator
    from app.modules_v2.product_cover_generator import ProductCoverGenerator
    from app.modules_v2.social_visual_generator import SocialVisualGenerator
    from app.modules_v2.visual_ranker import VisualRanker

    exporter = ContentExporter().generate(
        topic="Topic",
        run_folder="data/runs/test/export",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"artifact_paths": ["data/artifacts/a.md"]},
    )
    assert "export_folder" in exporter.summary

    ctl = PublishController().generate(
        topic="Topic",
        run_folder="data/runs/test/publish",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"auto_publish": False, "dry_run": True},
    )
    assert "auto_publish" in ctl.summary

    gum = GumroadPublisher().generate(
        topic="Topic",
        run_folder="data/runs/test/gum",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"auto_publish": False, "dry_run": True},
    )
    assert "status" in gum.summary
    assert "product_url" in gum.summary

    yt = YoutubePublisher().generate(
        topic="Topic",
        run_folder="data/runs/test/yt",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["youtube"],
        constraints={"auto_publish": False, "dry_run": True},
    )
    assert "status" in yt.summary
    assert "video_url" in yt.summary

    newsletter = NewsletterPackager().generate(
        topic="Topic",
        run_folder="data/runs/test/newsletter",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["newsletter"],
        constraints={},
    )
    assert "newsletter_issue_draft" in newsletter.summary
    assert "free_version_teaser" in newsletter.summary
    assert "premium_version_section" in newsletter.summary
    assert "upgrade_cta" in newsletter.summary
    assert "beehiiv_export" in newsletter.summary

    social = SocialLaunchPackager().generate(
        topic="Topic",
        run_folder="data/runs/test/social",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["x", "instagram"],
        constraints={},
    )
    assert "x_launch_post" in social.summary
    assert "shortform_launch_snippets" in social.summary

    payhip = PayhipPackager().generate(
        topic="Topic",
        run_folder="data/runs/test/payhip",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["payhip"],
        constraints={"artifact_paths": ["data/artifacts/a.md"]},
    )
    assert "product_title" in payhip.summary
    assert "upload_checklist" in payhip.summary

    image = ImageGeneratorV2().generate(
        topic="Topic",
        run_folder="data/runs/test/image",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["youtube"],
        constraints={"style": "cinematic", "num_images": 2, "use_api_fallback": False},
    )
    assert "image_paths" in image.summary
    assert "prompts_used" in image.summary

    thumb = ThumbnailGenerator().generate(
        topic="Topic",
        run_folder="data/runs/test/thumb",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["youtube"],
        constraints={"title": "Big Promise", "hook": "No fluff", "num_variants": 2, "use_api_fallback": False},
    )
    assert "ranked_thumbnail_paths" in thumb.summary
    assert "best_thumbnail_path" in thumb.summary
    assert "preferred_final_asset" in thumb.summary

    cover = ProductCoverGenerator().generate(
        topic="Topic",
        run_folder="data/runs/test/cover",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"num_images": 2, "use_api_fallback": False},
    )
    assert "product_cover_paths" in cover.summary
    assert "preferred_final_asset" in cover.summary

    social_visual = SocialVisualGenerator().generate(
        topic="Topic",
        run_folder="data/runs/test/social_visual",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["x"],
        constraints={"channel": "x", "num_images": 2, "use_api_fallback": False},
    )
    assert "social_visual_paths" in social_visual.summary
    assert "preferred_final_asset" in social_visual.summary

    rank = VisualRanker().generate(
        topic="Topic",
        run_folder="data/runs/test/rank",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["youtube"],
        constraints={"image_paths": image.summary.get("image_paths") or [], "title": "Title", "hook": "Hook"},
    )
    assert "ranked_images" in rank.summary


def test_publish_gating_and_credential_behaviors(monkeypatch):
    from app.modules_v2.gumroad_publisher import GumroadPublisher
    from app.modules_v2.youtube_publisher import YoutubePublisher
    from app.modules_v2.newsletter_packager import NewsletterPackager
    from app.modules_v2.social_launch_packager import SocialLaunchPackager
    from app.modules_v2.payhip_packager import PayhipPackager
    from app.modules_v2.image_generator_v2 import ImageGeneratorV2

    monkeypatch.delenv("EV_GUMROAD_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("EV_YOUTUBE_ACCESS_TOKEN", raising=False)

    gum_skipped = GumroadPublisher().generate(
        topic="Topic",
        run_folder="data/runs/test/gum_skip",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"auto_publish": False, "dry_run": False, "publish_to_gumroad": True},
    )
    assert gum_skipped.summary.get("status") == "skipped"

    gum_dry = GumroadPublisher().generate(
        topic="Topic",
        run_folder="data/runs/test/gum_dry",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"auto_publish": True, "dry_run": True, "publish_to_gumroad": True},
    )
    assert gum_dry.summary.get("status") == "simulated"

    gum_missing = GumroadPublisher().generate(
        topic="Topic",
        run_folder="data/runs/test/gum_missing",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"auto_publish": True, "dry_run": False, "publish_to_gumroad": True},
    )
    assert gum_missing.summary.get("status") == "missing_credentials"

    yt_dry = YoutubePublisher().generate(
        topic="Topic",
        run_folder="data/runs/test/yt_dry",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["youtube"],
        constraints={"auto_publish": True, "dry_run": True, "publish_to_youtube": True},
    )
    assert yt_dry.summary.get("status") == "simulated"

    yt_missing = YoutubePublisher().generate(
        topic="Topic",
        run_folder="data/runs/test/yt_missing",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["youtube"],
        constraints={"auto_publish": True, "dry_run": False, "publish_to_youtube": True},
    )
    assert yt_missing.summary.get("status") == "missing_credentials"


def test_content_exporter_bundle_structure():
    from app.modules_v2.content_exporter import ContentExporter

    res = ContentExporter().generate(
        topic="Topic",
        run_folder="data/runs/test/export_bundle",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={
            "artifact_paths": ["data/artifacts/a.md"],
            "workflow_step_metadata": {
                "product_packager": {
                    "product_name": "Topic Money Pack",
                    "product_description": "Short desc",
                    "price_suggestion": "$29",
                    "bundle_contents": ["a.md"],
                },
                "sales_copy_generator": {
                    "full_description": "Long desc",
                    "bullet_points": ["b1", "b2"],
                },
                "distribution_generator": {
                    "youtube_title": "YT Title",
                    "youtube_description": "YT Desc",
                    "youtube_tags": ["tag1"],
                    "youtube_pinned_comment": "Pinned",
                    "youtube_cta": "CTA",
                    "twitter_launch_post": "Launch",
                    "twitter_thread": ["1", "2"],
                    "twitter_cta_variants": ["c1"],
                    "newsletter_draft": "News draft",
                    "email_promo": "Promo",
                    "email_cta_variants": ["cta"],
                    "tiktok_hooks": ["h1"],
                    "instagram_caption": "insta",
                    "linkedin_post": "linkedin",
                    "reel_short_captions": ["r1"],
                },
            },
        },
    )
    packs = res.summary.get("packs") or {}
    assert "youtube" in packs
    assert "gumroad" in packs
    assert "newsletter" in packs
    assert "premium" in packs
    assert "payhip" in packs
    assert "social" in packs
    assert "gumroad_bonus" in packs
    assert "youtube_supporting" in packs
    assert "logs" in packs


def test_thumbnail_generator_fallback_ranking_when_vision_fx_unavailable(monkeypatch):
    from app.modules_v2.thumbnail_generator import ThumbnailGenerator

    monkeypatch.delenv("EV_VISION_FX_CMD", raising=False)
    out = ThumbnailGenerator().generate(
        topic="Fallback Topic",
        run_folder="data/runs/test/thumb_fallback",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["youtube"],
        constraints={"title": "Fallback", "hook": "Hook", "num_variants": 2, "use_api_fallback": False},
    )
    assert "ranking_metadata" in out.summary
    assert out.summary.get("ranking_metadata", {}).get("method") in {"fallback", "vision_fx"}


def test_content_exporter_surfaces_preferred_final_assets():
    from app.modules_v2.content_exporter import ContentExporter

    res = ContentExporter().generate(
        topic="Topic",
        run_folder="data/runs/test/export_pref",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={
            "artifact_paths": ["data/artifacts/a.md"],
            "workflow_step_metadata": {
                "thumbnail_generator": {"v2_summary": {"preferred_final_asset": "data/final/thumb.png"}},
                "product_cover_generator": {"v2_summary": {"preferred_final_asset": "data/final/cover.png"}},
                "social_visual_generator": {"v2_summary": {"preferred_final_asset": "data/final/social.png"}},
                "product_packager": {"product_name": "Topic Money Pack", "product_description": "Short", "price_suggestion": "$29", "bundle_contents": ["a.md"]},
                "sales_copy_generator": {"full_description": "Long", "bullet_points": ["b1"]},
                "distribution_generator": {"youtube_title": "YT", "youtube_description": "Desc", "twitter_launch_post": "Launch", "twitter_thread": ["1"]},
            },
        },
    )
    pref = res.summary.get("preferred_final_assets") or {}
    assert pref.get("final_thumbnail") == "data/final/thumb.png"
    assert pref.get("final_product_cover") == "data/final/cover.png"
    assert pref.get("final_social_visual") == "data/final/social.png"


def test_helion_batch1_modules_basic_outputs():
    from app.modules_v2.prediction_tracker import PredictionTracker
    from app.modules_v2.trend_surfer import TrendSurfer
    from app.modules_v2.idea_miner import IdeaMiner
    from app.modules_v2.sales_page_builder import SalesPageBuilder
    from app.modules_v2.email_sequence_builder import EmailSequenceBuilder
    from app.modules_v2.cross_pollinator import CrossPollinator

    trend = TrendSurfer().generate(
        topic="Creator AI",
        run_folder="data/runs/test/trend_surfer",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"keywords": ["creator ai", "automation"], "create_predictions": True},
    )
    assert "trend_signals" in trend.summary
    assert "prediction_candidates" in trend.summary

    tracker = PredictionTracker().generate(
        topic="Creator AI",
        run_folder="data/runs/test/prediction_tracker",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"action": "add", "prediction_text": "Creator AI demand will rise", "confidence": 0.7},
    )
    assert tracker.summary.get("db_path")
    listed = PredictionTracker().generate(
        topic="Creator AI",
        run_folder="data/runs/test/prediction_tracker",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"action": "list", "db_path": tracker.summary.get("db_path")},
    )
    assert isinstance(listed.summary.get("predictions", []), list)

    ideas = IdeaMiner().generate(
        topic="Creator AI",
        run_folder="data/runs/test/idea_miner",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={},
    )
    assert "workflow_suggestions" in ideas.summary

    sales = SalesPageBuilder().generate(
        topic="Creator AI",
        run_folder="data/runs/test/sales_page_builder",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"product_name": "Creator AI Kit"},
    )
    assert "sales_page" in sales.summary

    emails = EmailSequenceBuilder().generate(
        topic="Creator AI",
        run_folder="data/runs/test/email_sequence_builder",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["newsletter"],
        constraints={"emails": 4},
    )
    assert "email_sequence" in emails.summary

    cross = CrossPollinator().generate(
        topic="Creator AI",
        run_folder="data/runs/test/cross_pollinator",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"context": "automation systems", "vault_notes": ["creator monetization", "automation workflows"]},
    )
    assert "bridges" in cross.summary


def test_batch2_modules_generate_and_fallback(monkeypatch):
    from app.modules_v2.thread_bomber import ThreadBomber
    from app.modules_v2.short_form_pack import ShortFormPack
    from app.modules_v2.competitor_dissector import CompetitorDissector
    from app.modules_v2.vault_auditor import VaultAuditor
    from app.modules_v2.comfyui_director import ComfyUIDirector

    th = ThreadBomber().generate(
        topic="Topic",
        run_folder="data/runs/test/thread_bomber",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["x"],
        constraints={},
    )
    assert "x_thread" in th.summary

    sf = ShortFormPack().generate(
        topic="Topic",
        run_folder="data/runs/test/short_form_pack",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["tiktok"],
        constraints={"clips": 4},
    )
    assert "short_form_pack" in sf.summary

    cd = CompetitorDissector().generate(
        topic="Topic",
        run_folder="data/runs/test/competitor_dissector",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"competitors": ["A", "B"]},
    )
    assert "competitor_analysis" in cd.summary

    va = VaultAuditor().generate(
        topic="Topic",
        run_folder="data/runs/test/vault_auditor",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["gumroad"],
        constraints={"context": "abc", "artifact_paths": ["data/artifacts/a.md"]},
    )
    assert "audit" in va.summary

    monkeypatch.setattr("app.local_services.visual_fx_bridge_client.requests.post", lambda *a, **k: (_ for _ in ()).throw(Exception("offline")))
    monkeypatch.setattr("app.modules_v2.comfyui_connector.is_comfyui_running", lambda *a, **k: False)
    monkeypatch.setattr("app.modules_v2.image_generator_v2.ImageGeneratorV2._generate_via_openai", lambda *a, **k: False)

    director = ComfyUIDirector().generate(
        topic="Topic",
        run_folder="data/runs/test/comfyui_director",
        sku="EVTEST",
        tier="core",
        price_cents=1000,
        platforms=["youtube"],
        constraints={"num_images": 1, "use_api_fallback": False},
    )
    assert "mode" in director.summary
    assert "bridge_attempt" in director.summary
