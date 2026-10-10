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


## OpenBlueprint CAD producer

The native openblueprint_floor_plan module creates locally generated concept floor plans and SHA-256 digest receipts. Import the resulting JSON through OpenBlueprint's **EVIE CAD** review gate; never auto-import. See docs/OPENBLUEPRINT_CAD_HANDOFF.md. This is a new module, not a recovered original Sovereign Shelf CAD card.


## Recovered Sovereign Shelf Architecture Pack (Rung 3)

Eleven original Architecture Pack card definitions and two ritual sequences are available as authenticated read-only metadata at GET /v1/shelf/architecture. The bounded OpenBlueprint producer is linked to the historical Floor Plan Generator card but does not implement its original structure_spec input or DXF/SVG outputs. Other cards are catalog-only. See docs/SOVEREIGN_SHELF_ARCHITECTURE_R3.md.


## Public React website (EVIE Commons Porch)

The static, public React/Vite interface lives in [`web/`](web/README.md). It features a searchable Sovereign Shelf Architecture catalog, recovered ritual sequences, and a browser-only sample OpenBlueprint handoff. No API key, vault content, or Python module execution is exposed by GitHub Pages.

**Expected GitHub Pages address:** https://michaelwave369.github.io/EVIE/ (available after merging the frontend and selecting **GitHub Actions** in Settings → Pages). The static porch is **not** the local authenticated EVIE API or a hosted Streamlit dashboard.


## Full Nested Sovereign Shelf

The EVIE React public porch now explores a reviewed, sanitized historical catalog of all 159 unique cards nested under 9 packs, with 7 card classes, linked rituals, compatible-card trails and a design-only deck composer. The original 11-card Architecture Pack remains available. The deck does not execute, import, authorize or operate EVIE's private API. See [Rung 4 public Shelf documentation](docs/PUBLIC_NESTED_SHELF_R4.md).


## Local EVIE revival (Rung 5)

Developer launchers now use loopback networking and protected API endpoints fail closed on blank/known sample keys. Audit registry links and optionally run one real disposable CAD producer smoke with `python -m tools.evie_doctor --json --smoke-cad`. This does not claim all registered modules work. See [EVIE Local Revival](docs/EVIE_LOCAL_REVIVAL_R5.md).


## Capability Mission Control (R6)

The React sidebar now includes **Mission Control**, an indexed public snapshot of the **real source-registered Python modules** and **configured workflows** (separate from the 159 historical Shelf cards). It lets visitors search and inspect module registrations, dependency references, workflow steps, and targeted test-source evidence. The snapshot is generated directly from `app/modules/__init__.py` and `configs/workflows.json` on every web build, never from credentials or local runtime probes. No claim is made that all modules are runnable. See [R6 evidence and limitations](docs/EVIE_MISSION_CONTROL_R6.md).


## Capability Qualification Lab (R7)

EVIE now has an explicitly allowlisted **local subprocess qualification runner** for only the bounded OpenBlueprint concept floor-plan producer. Run `python -m tools.evie_qualify list`, then `python -m tools.evie_qualify run openblueprint_floor_plan --receipt ./cad-qualification.json` in your local clone. The receipt records a fixed-schema, digest-checked disposable fixture, and does **not** authorize agents to act or claim production readiness. A browser-only inspector appears under Mission Control → Qualification Lab; it checks source-version and schema but **never authenticates** an unsigned receipt or changes the public live-qualified count. See [R7 qualification protocol](docs/EVIE_QUALIFICATION_LAB_R7.md).


## R8: Signed local qualification attestations

Use `python -m tools.evie_attest keygen --private ./evie-local.pem --public ./evie-trusted.pub.pem` to generate an encrypted local Ed25519 private key and independently shareable public key. Sign a **fresh passing** CAD qualification using `python -m tools.evie_qualify run openblueprint_floor_plan --signing-key ./evie-local.pem --attestation ./cad-run.attestation.json`. Verify with `python -m tools.evie_attest verify --attestation ./cad-run.attestation.json --trusted-public ./evie-trusted.pub.pem`. The React Qualification Lab provides optional browser-only signature verification using a separately selected trusted public PEM. A valid signature grants no job permissions. See [Signed Evidence R8](docs/EVIE_SIGNED_ATTESTATION_R8.md).


## R8B: EVIE Family Permission Gate (review only)

The local family-gate CLI can create a digest-bound, short-lived artifact review proposal, acknowledge it with your encrypted Ed25519 private key, and verify the acknowledgement against an independently selected trusted public key. **This does not grant execution permission or transfer a file.** Six family targets have proposed artifact contracts only, and all transports remain disabled. Use `python -m tools.evie_family_gate catalog` to inspect them. The public React **Family Gate** tab can generate the same review envelope from a local file entirely in your browser. See [Family Gate R8B](docs/EVIE_FAMILY_GATE_R8B.md).


## R9: Read-only OpenBlue artifact preflight

EVIE can now compare an actual OpenBlue-compatible EVIE proposal against its R8B `evie.family-handoff-proposal/1` review envelope, verifying exact SHA-256 bytes, size, expiration, target, and a conservative mirror of the reviewed OpenBlueprint importer geometry rules. From the local clone run `python -m tools.evie_family_gate inspect-openblue --proposal ./review.proposal.json --artifact ./plan.json`. The public **Family Gate → OpenBlue handoff check** offers a browser-only two-file inspector. These checks do not upload anything, modify OpenBlue or imply OpenBlue accepted the plan. The existing OpenBlue importer must separately preview and get your explicit approval. [Read R9 preflight protocol](docs/EVIE_OPENBLUE_PREFLIGHT_R9.md).


## R10: OpenBlue real-parser contract replay

EVIE can now replay an actual OpenBlue `parseEvieProposal` implementation from a **local, trusted, explicitly git-revision-pinned OpenBlue checkout**. This is stronger parser-compatibility evidence than EVIE's own R9 geometry mirror, while remaining **read-only and non-authorizing**. Use `node tools/openblue_parser_replay.mjs --openblue-dir ../OpenBlueprintStudio --expected-revision YOUR_VERIFIED_COMMIT_SHA --proposal ./review.proposal.json --artifact ./plan.json --receipt ./openblue-parser-replay.json`. An additional GitHub Actions job checks the two repos together using a pinned OpenBlue commit. The unsigned local replay can be inspected in Family Gate after a matching R9 preflight. It is **not** a recipient-issued acknowledgment or a UI import approval. [R10 replay guide](docs/EVIE_OPENBLUE_PARSER_REPLAY_R10.md).


## R11: EVIE → FieldDeck review blueprint handoff

The public **Family Gate → EVIE meets FieldDeck** now inspects EVIE's design-only Shelf decks and lets the human independently assemble 1–6 reviewed FieldDeck action steps. It exports a valid `fielddeck.chain.blueprint` v0.5 JSON with **execution denied**, for manual import into FieldDeck's Chain Lab. No automatic mapping exists between 159 historical Shelf cards and FieldDeck's three allowlisted diagnostics. A **pinned two-repository CI workflow** runs FieldDeck's actual parser to prove schema compatibility, not runtime execution. [Details and limits](docs/EVIE_FIELDDECK_HANDOFF_R11.md).


## R12: Workflow Revival Studio (pure preflight)

Mission Control now includes **Workflow Studio** to inspect EVIE's original ten configured workflows, expand nested steps, simulate optional conditions and export a source-bound **non-executable** review plan. This is separate from legacy `run_workflow(...,dry_run=True)`, which writes a database run record. The new `python -m app.workflows.preflight --workflow vault_to_lesson_pack --enable include_audio` uses source text only, does not import the module registry, call providers or touch the DB. Every step and report denies execution. [Read R12 planning protocol](docs/EVIE_WORKFLOW_STUDIO_R12.md).


## R13: Supervised fixed CAD workflow (first actual local execution)

Unlike R12's read-only plans, R13 **actually runs one audited local workflow step**: `openblueprint_concept_floor_plan` calling the genuine `openblueprint_floor_plan` producer. Use `python -m tools.evie_supervised run openblueprint_concept_floor_plan --stage-dir ../evie-cad-review-001 --confirm-local-execution` from the EVIE checkout. It runs a fixed 24 × 16 ft scenario in a disposable credential-stripped Python child process (not an OS sandbox), checks geometry/digests, and stages a blueprint, original source-only preflight, and **unsigned** review receipt into a new directory outside the repo. `Mission Control → Workflow Studio → Supervised CAD Run` can inspect that local pair without uploading or approving a CAD import. No database, external provider, publishing or generalized workflow execution is enabled. [R13 protocol](docs/EVIE_SUPERVISED_CAD_R13.md).


## R14: First supervised local content output

EVIE's new **`local_content_hooks_review`** workflow runs the existing v2 `HooksGenerator` for an explicitly selected UTF-8 script, producing **nine editable content hooks** without a model, provider API or publisher. Use `python -m tools.evie_supervised_hooks local_content_hooks_review --script-file ./draft.txt --topic "EVIE Creator Loop" --stage-dir ../evie-hooks-review-001 --confirm-local-execution`. The staged four-file bundle includes JSON, Markdown review sheet, R12 source plan and an unsigned digest-bound observation. **Workflow Studio → Nine-Hook Content Workshop** can inspect local files in the browser, never upload or approve publishing. Only this fixed one-step workflow is allowlisted; the child process is not a hard sandbox. See [R14](docs/EVIE_SUPERVISED_HOOKS_R14.md).


## R15: Two-step governed content handoff

The new `local_hooks_to_distribution_review` workflow is a two-module local route: R14 `hooks_generator` output is manually reviewed, its exact SHA-256 is explicitly confirmed, then EVIE's real v2 `DistributionGenerator` consumes the first five hooks. Use `python -m tools.evie_supervised_distribution --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_SHA256 --stage-dir ../evie-distribution-review-001 --confirm-local-execution`. The output is a review-only distribution JSON with an unsigned, non-authorizing receipt. Workflow Studio includes a four-file browser-only verification pane. No publishing, provider API, automatic step chaining, or recipient approval. See [R15 protocol](docs/EVIE_TWO_STEP_HANDOFF_R15.md).


## R16: Optional signed one-use local action leases

EVIE now has a stronger **Ed25519-signed** path for the R15 second-stage distribution draft. A short-lived `evie.local-action-lease/1` binds the exact hooks artifact SHA-256, current workflow source, destination fingerprint, signer and a maximum 20-second/32-KB budget. The **new** `tools.evie_approved_distribution` CLI atomically burns the nonce in a persistent operator-selected **local SQLite ledger** before running the real second module, blocking reuse against that same intact ledger. The original R15 operator-confirmed command remains available **without this enforcement**, and no public website can execute either command. EVIE's Workflow Studio includes an optional signing guide. No publishing approval, verified personal identity or network/OS sandbox is implied. [R16 signing and execution guide](docs/EVIE_LOCAL_ACTION_LEASE_R16.md).


## R17: Optional offline Docker capsule for R16 signed distribution

EVIE's signed R16 lane now has an additional, **strict Docker-isolated command**: `python -m tools.evie_isolated_distribution --hooks-dir ../evie-hooks-review-001 --approved-hooks-sha256 YOUR_REVIEWED_64_CHARACTER_SHA256 --stage-dir ../evie-distribution-review-001 --lease-file ../review.lease.json --trusted-public ../evie-lease-trusted-public.pem --ledger ../evie-local-lease-ledger.sqlite --confirm-local-execution`. It uses the same signed one-use approval and exact R14 artifact, but runs the real distribution generator in a minimal file capsule under Docker `--network=none --read-only`, nonroot, no capabilities, no privileges, bounded memory/CPU/processes, a tiny writable tmpfs and no host checkout mount. Docker Desktop/Engine and a trusted **preinstalled** `python:3.11-slim` image are required; the local command never pulls images and **never falls back** to host execution. The original non-Docker R15/R16 commands remain usable, so this is not a repository-wide isolation mandate. First-stage hooks execution is not covered. [R17 isolation protocol](docs/EVIE_DOCKER_CAPSULE_R17.md).


## R18: Governed two-stage local workflow controller

`python -m tools.evie_governed_flow plan|start|status|resume` coordinates genuine R14 hooks → explicit human review pause → independent R16 signed one-use lease → real R17 offline Docker distribution. The new-session controller produces create-exclusive local event records `01-hooks-paused.json`, `02-signed-resume-attempt.json`, and `03-distribution-staged.json`. A recorded uncertain attempt cannot be retried through this controller. It never signs its own approvals, publishes anything, runs a background queue or grants arbitrary-module execution. R14 Stage 1 remains a host subprocess without OS isolation. See [R18 flow guide](docs/EVIE_GOVERNED_FLOW_R18.md).


## R19: Both stages of the governed content workflow use Docker

The R18 `tools.evie_governed_flow start` command now **requires an installed local Docker Engine and preinstalled `python:3.11-slim` image**. It executes the real R14 HooksGenerator in its own minimal, offline, read-only source capsule, then pauses for human review. The previously signed R17 offline Docker distribution resume remains unchanged. The new controller refuses missing Docker with **no host fallback for either stage** and records the isolated Stage 1 profile as unsigned local evidence. Pre-R19 host-started sessions remain inspectable but cannot resume through R19; create a new session. Older R14/R15/R16 standalone host commands remain accessible as explicitly documented legacy paths; Docker isolation is **not** universal repo enforcement. See [R19 dual-capsule design](docs/EVIE_HOOKS_DOCKER_R19.md).
