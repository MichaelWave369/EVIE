# EVIE — EmberVault Income Engine

> **Phi Commons edition.** EVIE is preserved as an open, local-first capability and workflow engine. Its original productization/publishing mission remains visible in the code, but the modern Commons role is broader: reusable modules, workflows, vault patterns, bridges, and artifact pipelines for people to inspect, remix, and integrate into systems such as PhiOS.


## 🚀 What EVIE Is
EVIE is a **local-first AI content + income engine**.

It combines:
- a private vault (your data, your machine)
- RAG-powered generation
- modular automation
- media workflows

The goal is simple: **turn knowledge into usable products and assets**.

---

## ⚡ Core Capabilities

### 1) Content Generation
Generate structured assets from a topic or vault context:
- ebooks and long-form drafts
- scripts and outlines
- newsletters and social derivatives
- study materials

### 2) Media Generation
Create media-ready outputs from the same source:
- slide decks (PPTX)
- infographic images (PNG)
- podcast-style script + optional audio
- optional video assembly from slides + audio

### 3) Workflow Automation
Chain modules into repeatable pipelines:
- `vault_to_lesson_pack`
- offer/factory workflows
- scheduled task execution

### 4) Vault + RAG System
- ingest docs/files/text into a local vault
- retrieve relevant context
- run topic-specific generation with traceable artifacts

### 5) Productization
Package outputs for publishing/sales workflows:
- bundles and registries
- SEO/storefront-oriented artifacts
- reusable content pipelines

---

## 🧠 Key Concept
EVIE is designed around this loop:

**Vault → Modules → Workflows → Artifacts**

- **Vault** stores source knowledge.
- **Modules** generate specific outputs.
- **Workflows** orchestrate multi-step pipelines.
- **Artifacts** are saved under `data/` for reuse, packaging, and publishing.

Local-first means you can run core flows without sending your entire system state to a hosted SaaS control plane.

---

## 🛠️ Quickstart (Local)

### 1) Install
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Setup env
```bash
cp .env.example .env
# edit .env and set at least EV_API_KEY + your chosen model settings
```

### 3) Run API
```bash
bash start_api.sh
# API docs: http://127.0.0.1:18791/docs
```

### 4) Run dashboard
```bash
bash start_dashboard.sh
# Dashboard: http://127.0.0.1:8501
```

---

## 🎬 Example: Lesson Pack Workflow
`vault_to_lesson_pack` is the primary end-to-end workflow.

### Input
- `topic`
- optional `context`
- optional `artifact_paths`
- optional flags: `include_audio`, `include_video`

### Default steps
1. `podcast_script_generator`
2. `presentation_generator`
3. `infographic_generator`
4. `study_module`

### Optional steps
- `audio_generator` (if `include_audio=true`)
- `video_generator` (if `include_video=true`)

### Output
A coherent lesson/media pack across text + visual (and optionally audio/video) artifacts stored under EVIE-managed paths in `data/`.

### Input
- `topic`
- optional `context`
- optional `artifact_paths`
- optional flags: `include_audio`, `include_video`

## 🧩 Architecture Overview
- **FastAPI backend**: module/workflow/run APIs
- **Modules**: single-purpose generators
- **Workflows**: multi-module orchestration
- **Scheduler/Factory**: queued + recurring automation
- **Streamlit dashboard**: operator UI for runs and workflows

---

## ⚙️ Configuration
EVIE reads configuration from `.env`.

### Baseline settings
- `EV_API_KEY`
- `EV_DATA_DIR`
- `EV_DB_PATH`
- `EV_LLM_BACKEND` + provider-specific keys
- `EV_EMBED_BACKEND`

### LLM + embeddings
Choose one LLM backend (OpenAI / Anthropic / Ollama) and one embedding backend (hash/OpenAI/Ollama/etc.) in `.env.example`.

### Optional media config
For media modules, you may also configure:
- `EV_ELEVENLABS_API_KEY`
- `EV_VOICE_HOST_A`
- `EV_VOICE_HOST_B`

---

## 🌐 Deployment (First Pass)
EVIE supports a practical two-service deployment model:

1. **API service** (FastAPI)
2. **Dashboard service** (Streamlit)

This repo includes:
- `Dockerfile`
- `docker-compose.yml`
- `render.yaml` (first-pass hosted blueprint)

### Hosted essentials
- Set `EV_API_KEY` for API and dashboard.
- Set `EV_API_BASE` on dashboard to your deployed API URL.

---

## ⚠️ Media Dependencies (Important)
Media is optional.

Core text/slide/infographic/study flows can still run when media dependencies are unavailable.

For media features:
- `ffmpeg`
- `moviepy`
- `pillow`
- `pydub`
- `Node.js` (presentation rendering path)
- `EV_ELEVENLABS_API_KEY` (for ElevenLabs audio)

If missing, EVIE returns structured dependency errors and workflows can complete as **partial** rather than hard-failing the full pipeline.

---

## 🚀 Publish Layer (Auto + Export-First)
EVIE supports a controlled publish workflow: `vault_to_money_publish`.

Safety model:
- `auto_publish=false` → export only (no platform publish attempts)
- `dry_run=true` → simulate publishing, generate logs/results, no live publish
- channel failures return structured statuses and workflows can finish as partial

### Real publish targets (credentialed)
- **Gumroad** product creation via API (`EV_GUMROAD_ACCESS_TOKEN`)
- **YouTube** upload via API (`EV_YOUTUBE_ACCESS_TOKEN`)

### Export-first targets (manual posting packs)
- X / Twitter
- Newsletter (Beehiiv / ConvertKit style)
- TikTok / Instagram / LinkedIn short-form packs
- Payhip storefront listing packs (manual export)

Newsletter/social export modules:
- `newsletter_packager` (issue draft, promo email, subject options, Beehiiv/ConvertKit copy blocks)
- `social_launch_packager` (X launch + thread, TikTok/Instagram/LinkedIn copy, CTA variants)

When credentials are missing, EVIE keeps generating publish-ready exports and records clear `missing_credentials` statuses.

### Real publish targets (credentialed)
- **Gumroad** product creation via API (`EV_GUMROAD_ACCESS_TOKEN`)
- **YouTube** upload via API (`EV_YOUTUBE_ACCESS_TOKEN`)


### AI images: `image_generator_v2` (local-first)
EVIE supports local-first AI image generation for thumbnails/product/social visuals:
- primary path: local ComfyUI (`EV_COMFYUI_URL`, default `http://127.0.0.1:8188`)
- fallback path: OpenAI image API when API fallback is enabled and OpenAI key is configured

Typical constraints:
- `generate_images` (bool)
- `image_style` (`cinematic`, `product`, `social`, `minimal`, `cosmic`)
- `num_images` (1-8)

Outputs include generated image file paths, prompts used, and variation metadata.





### Local Visual FX Bridge (EXE handoff service)
EVIE includes a local FastAPI bridge for desktop EXE tools that do not expose APIs:
- Render FX 1.0
- Vector FX 1.0
- Vision FX 2.0

Bridge file:
- `tools/visual_fx_bridge.py`

Run locally:
```bash
python tools/visual_fx_bridge.py
```

Default local endpoints:
- `GET /health`
- `GET /jobs`
- `POST /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/complete`
- `POST /jobs/{job_id}/approve` (mark a returned file as preferred final asset category)
- automatic output detection on job fetch/list (marks `output_detected` or auto-completes if enabled)
- `POST /vision-fx/handoff`
- `POST /render-fx/handoff`
- `POST /vector-fx/handoff`

Job folders are written under `data/visual_fx_bridge/jobs/<job_id>/` with:
- `input/`
- `output/`
- `meta.json`
- `status.json`
- `logs.txt`

Manual completion flow:
1. EVIE submits a handoff job to bridge.
2. Bridge copies inputs into `input/`.
3. User processes in EXE tool and puts final outputs into `output/`.
4. When outputs are found, job moves to `output_detected` (or `completed` if auto-complete is enabled).
5. Otherwise (or if preferred), mark job complete via `/jobs/{job_id}/complete`.

Optional convenience launch:
- Configure `EV_VISION_FX_EXE`, `EV_RENDER_FX_EXE`, `EV_VECTOR_FX_EXE`.
- Bridge may launch the EXE, but jobs remain manual until completed explicitly.

Preferred final asset categories:
- `final_thumbnail`
- `final_product_cover`
- `final_social_visual`

Bridge status flow:
- `created` → `queued` → `awaiting_external_processing` → `output_detected` → `completed`
- Optional auto-complete on detected outputs via env: `EV_VISUAL_FX_AUTO_COMPLETE_ON_OUTPUT=true`

Bridge safety model:
- local-only by default
- no fake API automation claims for EXE tools
- graceful fallback when bridge is offline

### Second-pass visual pipeline (local-first)
EVIE now includes modular second-pass visual generation and ranking:
- `thumbnail_generator`
- `product_cover_generator`
- `social_visual_generator`
- `visual_ranker`

Conceptual chain:
`EVIE prompt builder -> image_generator_v2/ComfyUI -> Render FX -> Vision FX ranking -> Vector FX polish`

Current integration model is production-safe and explicit:
- `image_generator_v2` + ComfyUI are real integrations.
- Render FX / Vision FX / Vector FX are connector scaffolds with clear TODO boundaries and graceful passthrough fallback when command endpoints are not configured.

New workflow constraints (optional):
- `generate_thumbnails`
- `generate_product_covers`
- `generate_social_visuals`

Final asset mechanism:
- Visual modules now persist preferred selections in `visual_final_assets.json` within run folders.
- Bridge jobs can mark returned files as final via `POST /jobs/{job_id}/approve`.
- Preferred keys used in publish/export summaries: `final_thumbnail`, `final_product_cover`, `final_social_visual`.

Thumbnail outputs include:
- `ranked_thumbnail_paths`
- `best_thumbnail_path`
- `prompts_used`
- `ranking_metadata`
- `text_safe_composition_notes`

### Recurring-income workflow: `vault_to_membership_pack`
Use this workflow to produce a weekly member-style bundle from one topic:
- lesson/media assets (script, slides, infographic, study)
- newsletter issue draft with free teaser + premium section + upgrade CTA
- social launch kit
- premium bonus asset summary
- optional Gumroad bonus export pack (`export_gumroad_bonus=true`)
- optional YouTube supporting content pack (`export_youtube_supporting_content=true`)

This workflow is export-first/manual by default and does not auto-publish to newsletter/social platforms.

### Publish export bundle structure
Each `vault_to_money_publish` run writes a copy/paste-ready bundle under `publish_export/` with:
- `youtube/`
- `gumroad/`
- `newsletter/`
- `premium/`
- `payhip/`
- `social/`
- `logs/`

---



### Helion Batch 1 strategic/conversion modules


Batch 2 module groups:
- **distribution**: `thread_bomber`, `short_form_pack`
- **intelligence**: `competitor_dissector`, `vault_auditor`
- **visual**: `comfyui_director` (bridge-first, ComfyUI fallback; does not replace `image_generator_v2`)
EVIE now includes these Batch 1 modules, integrated as standard modules/workflows:
- `prediction_tracker` (local SQLite prediction journal)
- `trend_surfer` (strategic trend signal + prediction candidate generation)
- `idea_miner` (monetization ideas + workflow suggestions)
- `sales_page_builder` (Gumroad/Payhip/storefront sales page blocks)
- `email_sequence_builder` (Beehiiv/ConvertKit/MailerLite-ready sequence drafts)
- `cross_pollinator` (vault intersection ideation)

Lightweight starter workflow:
- `helion_signal_to_offer` (trend -> prediction -> ideas -> sales page -> email sequence -> cross-pollination)
- `trend_to_money_publish` (trend strategy -> money pack -> optional publish workflow)



## ✅ Readiness + Smoke Tests
Before running full workflows, run lightweight checks:

```bash
python tools/check_readiness.py
python tools/run_smoke_tests.py
```

Readiness checks cover:
- core paths (`EV_DATA_DIR`, `EV_DB_PATH`)
- LLM backend config
- embeddings backend config
- ComfyUI reachability
- Visual FX bridge reachability
- Gumroad/YouTube credential presence
- OpenAI image fallback config

Smoke targets include:
- modules: `trend_surfer`, `idea_miner`, `sales_page_builder`, `email_sequence_builder`, `image_generator_v2`, `thumbnail_generator`
- workflows (dry-run): `vault_to_money_publish`, `vault_to_membership_pack`, `trend_to_money_publish`

## 📦 Output / Artifacts
Typical outputs include:
- script markdown (`.md`)
- slide decks (`.pptx`)
- infographics (`.png`)
- study assets (`.html`, `.json`, optional `.pdf`)
- optional audio (`.mp3`)
- optional video (`.mp4`)

Artifacts are written under EVIE-controlled `data/` paths for traceability and reuse.

---

## 🔮 Roadmap (Short)
- Better dashboard run inspection and artifact UX
- More prebuilt workflow templates
- Stronger hosted deployment presets and ops docs
- Expanded media pipeline reliability profiles


---

## Phi Commons status

Project-owned EVIE code and documentation in the clean Commons release are available under the **MIT License** unless otherwise noted.

EVIE is treated as a **donor system**, not a mandatory PhiOS dependency. Its strongest reusable ideas include:

- Vault → Modules → Workflows → Artifacts
- capability registries
- export-first publishing controls
- explicit partial/degraded workflow states
- local Visual FX handoff bridges
- readiness and smoke-test receipts
- local-first provider selection

For modern PhiOS integration, externally visible or mutating actions should pass through explicit PhiOS authority gates rather than inheriting historical EVIE permissions.

See `PHI_COMMONS.md`, `THIRD_PARTY_NOTICES.md`, `MODEL_LICENSES.md`, and `PUBLIC_RELEASE.md`.
