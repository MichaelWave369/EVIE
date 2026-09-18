from __future__ import annotations

from types import SimpleNamespace

from app.modules.base import ModuleResult
from app.workflows import runner


class _OkMod:
    def __init__(self, name: str, ext: str = ".txt"):
        self._name = name
        self._ext = ext

    def generate(self, topic, constraints):
        base = constraints.get("output_dir") or "data/artifacts/test"
        return ModuleResult(
            artifact_paths=[f"{base}/{self._name}{self._ext}"],
            metadata={"module": self._name},
        )


class _ErrMod:
    def __init__(self, name: str):
        self._name = name

    def generate(self, topic, constraints):
        return ModuleResult(
            artifact_paths=[],
            metadata={"v2_summary": {"error": f"{self._name} missing dep"}},
        )


def _mock_queries(monkeypatch):
    monkeypatch.setattr(runner.queries, "create_run", lambda **kwargs: 100)
    monkeypatch.setattr(runner.queries, "create_run_step", lambda **kwargs: kwargs.get("step_index", 0) + 1)
    monkeypatch.setattr(runner.queries, "finish_run_step", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner.queries, "finish_run", lambda *args, **kwargs: None)


def _mock_safety(monkeypatch):
    monkeypatch.setattr(runner, "validate_artifacts", lambda paths: SimpleNamespace(ok=True, checked=len(list(paths)), total_bytes=0, problems=[]))
    monkeypatch.setattr(runner, "run_code_gate", lambda paths: SimpleNamespace(ok=True, errors=[]))


def test_vault_to_lesson_pack_registered_in_workflows():
    names = [w["name"] for w in runner.list_workflows()]
    assert "vault_to_lesson_pack" in names
    assert "vault_to_money_pack" in names
    assert "vault_to_money_publish" in names
    assert "vault_to_membership_pack" in names
    assert "helion_signal_to_offer" in names
    assert "trend_to_money_publish" in names


def test_vault_to_lesson_pack_baseline_without_optional_media(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "audio_generator": _OkMod("audio_generator", ".mp3"),
            "video_generator": _OkMod("video_generator", ".mp4"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
        },
    )

    out = runner.run_workflow(
        "vault_to_lesson_pack",
        topic="Test Topic",
        constraints={"include_audio": False, "include_video": False},
    )
    modules = [s.get("module") for s in out["steps"] if s.get("status") != "skipped"]
    assert modules == [
        "podcast_script_generator",
        "presentation_generator",
        "infographic_generator",
        "study_module",
    ]
    assert out["status"] == "done"


def test_vault_to_lesson_pack_partial_when_optional_media_unavailable(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "audio_generator": _ErrMod("audio_generator"),
            "video_generator": _ErrMod("video_generator"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
        },
    )

    out = runner.run_workflow(
        "vault_to_lesson_pack",
        topic="Test Topic",
        constraints={"include_audio": True, "include_video": True},
    )
    partial_steps = [s for s in out["steps"] if s.get("status") == "partial"]
    assert out["status"] == "partial"
    assert len(partial_steps) == 2
    assert {s["module"] for s in partial_steps} == {"audio_generator", "video_generator"}


def test_vault_to_money_pack_baseline_run(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "hooks_generator": _OkMod("hooks_generator", ".json"),
            "product_packager": _OkMod("product_packager", ".json"),
            "sales_copy_generator": _OkMod("sales_copy_generator", ".json"),
            "distribution_generator": _OkMod("distribution_generator", ".json"),
            "audio_generator": _OkMod("audio_generator", ".mp3"),
            "video_generator": _OkMod("video_generator", ".mp4"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
        },
    )

    out = runner.run_workflow(
        "vault_to_money_pack",
        topic="Money Topic",
        constraints={"include_audio": False, "include_video": False},
    )
    modules = [s.get("module") for s in out["steps"] if s.get("status") != "skipped"]
    assert modules == [
        "podcast_script_generator",
        "presentation_generator",
        "infographic_generator",
        "study_module",
        "hooks_generator",
        "product_packager",
        "sales_copy_generator",
        "distribution_generator",
    ]
    assert out["status"] == "done"


def test_vault_to_money_publish_export_only(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "hooks_generator": _OkMod("hooks_generator", ".json"),
            "product_packager": _OkMod("product_packager", ".json"),
            "sales_copy_generator": _OkMod("sales_copy_generator", ".json"),
            "distribution_generator": _OkMod("distribution_generator", ".json"),
            "audio_generator": _OkMod("audio_generator", ".mp3"),
            "video_generator": _OkMod("video_generator", ".mp4"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
            "newsletter_packager": _OkMod("newsletter_packager", ".json"),
            "social_launch_packager": _OkMod("social_launch_packager", ".json"),
            "thread_bomber": _OkMod("thread_bomber", ".json"),
            "short_form_pack": _OkMod("short_form_pack", ".json"),
            "payhip_packager": _OkMod("payhip_packager", ".json"),
            "content_exporter": _OkMod("content_exporter", ".json"),
            "publish_controller": _OkMod("publish_controller", ".json"),
            "gumroad_publisher": _OkMod("gumroad_publisher", ".json"),
            "youtube_publisher": _OkMod("youtube_publisher", ".json"),
        },
    )

    out = runner.run_workflow(
        "vault_to_money_publish",
        topic="Publish Topic",
        constraints={"include_audio": False, "include_video": False, "auto_publish": False, "dry_run": True},
    )
    assert out["status"] == "done"
    modules = [s.get("module") for s in out["steps"]]
    assert "workflow:vault_to_money_pack" in modules
    skipped = [s for s in out["steps"] if s.get("status") == "skipped"]
    assert {s.get("module") for s in skipped} == {
        "gumroad_publisher",
        "youtube_publisher",
        "image_generator_v2",
        "thumbnail_generator",
        "product_cover_generator",
        "social_visual_generator",
        "thread_bomber",
        "short_form_pack",
    }


def test_vault_to_money_publish_partial_when_channel_fails(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "hooks_generator": _OkMod("hooks_generator", ".json"),
            "product_packager": _OkMod("product_packager", ".json"),
            "sales_copy_generator": _OkMod("sales_copy_generator", ".json"),
            "distribution_generator": _OkMod("distribution_generator", ".json"),
            "audio_generator": _OkMod("audio_generator", ".mp3"),
            "video_generator": _OkMod("video_generator", ".mp4"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
            "newsletter_packager": _OkMod("newsletter_packager", ".json"),
            "social_launch_packager": _OkMod("social_launch_packager", ".json"),
            "thread_bomber": _OkMod("thread_bomber", ".json"),
            "short_form_pack": _OkMod("short_form_pack", ".json"),
            "payhip_packager": _OkMod("payhip_packager", ".json"),
            "content_exporter": _OkMod("content_exporter", ".json"),
            "publish_controller": _OkMod("publish_controller", ".json"),
            "gumroad_publisher": _OkMod("gumroad_publisher", ".json"),
            "youtube_publisher": _ErrMod("youtube_publisher"),
        },
    )

    out = runner.run_workflow(
        "vault_to_money_publish",
        topic="Publish Topic",
        constraints={
            "include_audio": False,
            "include_video": False,
            "auto_publish": True,
            "dry_run": False,
            "publish_to_gumroad": True,
            "publish_to_youtube": True,
        },
    )
    assert out["status"] == "partial"
    partial = [s for s in out["steps"] if s.get("status") == "partial"]
    assert any(s.get("module") == "youtube_publisher" for s in partial)



def test_vault_to_membership_pack_baseline_run(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "audio_generator": _OkMod("audio_generator", ".mp3"),
            "video_generator": _OkMod("video_generator", ".mp4"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
            "newsletter_packager": _OkMod("newsletter_packager", ".json"),
            "social_launch_packager": _OkMod("social_launch_packager", ".json"),
            "thread_bomber": _OkMod("thread_bomber", ".json"),
            "short_form_pack": _OkMod("short_form_pack", ".json"),
            "product_packager": _OkMod("product_packager", ".json"),
            "sales_copy_generator": _OkMod("sales_copy_generator", ".json"),
            "payhip_packager": _OkMod("payhip_packager", ".json"),
            "content_exporter": _OkMod("content_exporter", ".json"),
        },
    )

    out = runner.run_workflow(
        "vault_to_membership_pack",
        topic="Member Topic",
        constraints={"include_audio": False, "include_video": False, "export_gumroad_bonus": True, "export_youtube_supporting_content": True},
    )
    assert out["status"] == "done"
    modules = [s.get("module") for s in out["steps"] if s.get("status") != "skipped"]
    assert modules == [
        "podcast_script_generator",
        "presentation_generator",
        "infographic_generator",
        "study_module",
        "newsletter_packager",
        "social_launch_packager",
        "product_packager",
        "sales_copy_generator",
        "payhip_packager",
        "content_exporter",
    ]


def test_vault_to_membership_pack_optional_media_partial(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "audio_generator": _ErrMod("audio_generator"),
            "video_generator": _ErrMod("video_generator"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
            "newsletter_packager": _OkMod("newsletter_packager", ".json"),
            "social_launch_packager": _OkMod("social_launch_packager", ".json"),
            "thread_bomber": _OkMod("thread_bomber", ".json"),
            "short_form_pack": _OkMod("short_form_pack", ".json"),
            "product_packager": _OkMod("product_packager", ".json"),
            "sales_copy_generator": _OkMod("sales_copy_generator", ".json"),
            "payhip_packager": _OkMod("payhip_packager", ".json"),
            "content_exporter": _OkMod("content_exporter", ".json"),
        },
    )

    out = runner.run_workflow(
        "vault_to_membership_pack",
        topic="Member Topic",
        constraints={"include_audio": True, "include_video": True},
    )
    assert out["status"] == "partial"
    partial = [s for s in out["steps"] if s.get("status") == "partial"]
    assert {s.get("module") for s in partial} == {"audio_generator", "video_generator"}



def test_vault_to_membership_pack_includes_image_step_when_enabled(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "audio_generator": _OkMod("audio_generator", ".mp3"),
            "video_generator": _OkMod("video_generator", ".mp4"),
            "newsletter_packager": _OkMod("newsletter_packager", ".json"),
            "social_launch_packager": _OkMod("social_launch_packager", ".json"),
            "thread_bomber": _OkMod("thread_bomber", ".json"),
            "short_form_pack": _OkMod("short_form_pack", ".json"),
            "product_packager": _OkMod("product_packager", ".json"),
            "sales_copy_generator": _OkMod("sales_copy_generator", ".json"),
            "payhip_packager": _OkMod("payhip_packager", ".json"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
            "content_exporter": _OkMod("content_exporter", ".json"),
        },
    )

    out = runner.run_workflow(
        "vault_to_membership_pack",
        topic="Member Topic",
        constraints={"generate_images": True, "image_style": "cinematic", "num_images": 2},
    )
    assert out["status"] == "done"
    modules = [s.get("module") for s in out["steps"] if s.get("status") != "skipped"]
    assert "image_generator_v2" in modules


def test_vault_to_money_pack_includes_new_visual_steps_when_enabled(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "hooks_generator": _OkMod("hooks_generator", ".json"),
            "product_packager": _OkMod("product_packager", ".json"),
            "sales_copy_generator": _OkMod("sales_copy_generator", ".json"),
            "distribution_generator": _OkMod("distribution_generator", ".json"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
            "audio_generator": _OkMod("audio_generator", ".mp3"),
            "video_generator": _OkMod("video_generator", ".mp4"),
        },
    )

    out = runner.run_workflow(
        "vault_to_money_pack",
        topic="Money Topic",
        constraints={"generate_thumbnails": True, "generate_product_covers": True, "generate_social_visuals": True},
    )
    modules = [s.get("module") for s in out["steps"] if s.get("status") != "skipped"]
    assert "thumbnail_generator" in modules
    assert "product_cover_generator" in modules
    assert "social_visual_generator" in modules


def test_helion_signal_to_offer_workflow_dry_run(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "trend_surfer": _OkMod("trend_surfer", ".json"),
            "prediction_tracker": _OkMod("prediction_tracker", ".json"),
            "idea_miner": _OkMod("idea_miner", ".json"),
            "sales_page_builder": _OkMod("sales_page_builder", ".json"),
            "email_sequence_builder": _OkMod("email_sequence_builder", ".json"),
            "cross_pollinator": _OkMod("cross_pollinator", ".json"),
        },
    )

    out = runner.run_workflow(
        "helion_signal_to_offer",
        topic="Creator AI",
        constraints={"create_predictions": True},
    )
    assert out["status"] == "done"
    modules = [s.get("module") for s in out["steps"]]
    assert modules == [
        "trend_surfer",
        "prediction_tracker",
        "idea_miner",
        "sales_page_builder",
        "email_sequence_builder",
        "cross_pollinator",
    ]


def test_trend_to_money_publish_baseline_run(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "trend_surfer": _OkMod("trend_surfer", ".json"),
            "prediction_tracker": _OkMod("prediction_tracker", ".json"),
            "idea_miner": _OkMod("idea_miner", ".json"),
            "cross_pollinator": _OkMod("cross_pollinator", ".json"),
            "sales_page_builder": _OkMod("sales_page_builder", ".json"),
            "email_sequence_builder": _OkMod("email_sequence_builder", ".json"),
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "hooks_generator": _OkMod("hooks_generator", ".json"),
            "product_packager": _OkMod("product_packager", ".json"),
            "sales_copy_generator": _OkMod("sales_copy_generator", ".json"),
            "distribution_generator": _OkMod("distribution_generator", ".json"),
            "audio_generator": _OkMod("audio_generator", ".mp3"),
            "video_generator": _OkMod("video_generator", ".mp4"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
            "newsletter_packager": _OkMod("newsletter_packager", ".json"),
            "social_launch_packager": _OkMod("social_launch_packager", ".json"),
            "thread_bomber": _OkMod("thread_bomber", ".json"),
            "short_form_pack": _OkMod("short_form_pack", ".json"),
            "payhip_packager": _OkMod("payhip_packager", ".json"),
            "content_exporter": _OkMod("content_exporter", ".json"),
            "publish_controller": _OkMod("publish_controller", ".json"),
            "gumroad_publisher": _OkMod("gumroad_publisher", ".json"),
            "youtube_publisher": _OkMod("youtube_publisher", ".json"),
        },
    )

    out = runner.run_workflow(
        "trend_to_money_publish",
        topic="Trend Topic",
        constraints={"create_predictions": True, "include_cross_pollination": False, "run_publish_workflow": False},
    )
    assert out["status"] == "done"
    modules = [s.get("module") for s in out["steps"]]
    assert "trend_surfer" in modules
    assert "prediction_tracker" in modules
    assert "workflow:vault_to_money_pack" in modules
    assert "sales_page_builder" in modules
    assert "email_sequence_builder" in modules
    sales_step = next(s for s in out["steps"] if s.get("module") == "sales_page_builder")
    assert isinstance(sales_step.get("metadata"), dict)
    skipped = [s for s in out["steps"] if s.get("status") == "skipped"]
    assert any(s.get("module") == "cross_pollinator" for s in skipped)
    assert any(s.get("module") == "workflow:vault_to_money_publish" for s in skipped)


def test_trend_to_money_publish_optional_publish_branch(monkeypatch):
    _mock_queries(monkeypatch)
    _mock_safety(monkeypatch)

    monkeypatch.setattr(
        runner,
        "REGISTRY",
        {
            "trend_surfer": _OkMod("trend_surfer", ".json"),
            "prediction_tracker": _OkMod("prediction_tracker", ".json"),
            "idea_miner": _OkMod("idea_miner", ".json"),
            "cross_pollinator": _OkMod("cross_pollinator", ".json"),
            "sales_page_builder": _OkMod("sales_page_builder", ".json"),
            "email_sequence_builder": _OkMod("email_sequence_builder", ".json"),
            "podcast_script_generator": _OkMod("podcast_script_generator", ".md"),
            "presentation_generator": _OkMod("presentation_generator", ".pptx"),
            "infographic_generator": _OkMod("infographic_generator", ".png"),
            "study_module": _OkMod("study_module", ".html"),
            "hooks_generator": _OkMod("hooks_generator", ".json"),
            "product_packager": _OkMod("product_packager", ".json"),
            "sales_copy_generator": _OkMod("sales_copy_generator", ".json"),
            "distribution_generator": _OkMod("distribution_generator", ".json"),
            "audio_generator": _OkMod("audio_generator", ".mp3"),
            "video_generator": _OkMod("video_generator", ".mp4"),
            "image_generator_v2": _OkMod("image_generator_v2", ".png"),
            "thumbnail_generator": _OkMod("thumbnail_generator", ".png"),
            "product_cover_generator": _OkMod("product_cover_generator", ".png"),
            "social_visual_generator": _OkMod("social_visual_generator", ".png"),
            "newsletter_packager": _OkMod("newsletter_packager", ".json"),
            "social_launch_packager": _OkMod("social_launch_packager", ".json"),
            "thread_bomber": _OkMod("thread_bomber", ".json"),
            "short_form_pack": _OkMod("short_form_pack", ".json"),
            "payhip_packager": _OkMod("payhip_packager", ".json"),
            "content_exporter": _OkMod("content_exporter", ".json"),
            "publish_controller": _OkMod("publish_controller", ".json"),
            "gumroad_publisher": _OkMod("gumroad_publisher", ".json"),
            "youtube_publisher": _OkMod("youtube_publisher", ".json"),
        },
    )

    out = runner.run_workflow(
        "trend_to_money_publish",
        topic="Trend Topic",
        constraints={
            "create_predictions": True,
            "include_cross_pollination": True,
            "run_publish_workflow": True,
            "include_thread_bomber": True,
            "include_short_form_pack": True,
        },
    )
    assert out["status"] == "done"
    modules = [s.get("module") for s in out["steps"]]
    assert "cross_pollinator" in modules
    assert "thread_bomber" in modules
    assert "short_form_pack" in modules
    assert "workflow:vault_to_money_publish" in modules
