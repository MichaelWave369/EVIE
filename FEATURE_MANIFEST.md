# EmberVault Income Engine — v3.2 Feature Manifest (Studio + Swarm)

Goal: **single unified build** with **no feature loss** across the v0.x → v3.1 lineage.

## Registered modules (82)
These modules are callable via API (`/v1/modules/{name}/run`) and visible in the dashboard.

### Core content lanes
- `ebooks`
- `youtube`
- `etsy`
- `newsletter`
- `affiliate`
- `pod`
- `stock`

### Automation & optimization
- `trend_miner`
- `repurposer`
- `offer_ladder`
- `conversion_packager`
- `pricing_optimizer`
- `review_miner`
- `support_macros`
- `metrics_optimizer`
- `offer_qa_gate`
- `ab_kit_generator`
- `inbox_faq_builder`
- `terms_generator`

### SEO, funnels, personalization
- `platform_packs`
- `seo_engine`
- `funnel_engine`
- `personalization_engine`
- `programmatic_seo_generator`
- `programmatic_seo_369`
- `funnel_compiler`
- `landing_finalizer`
- `seo_site_compiler`
- `seo_site_publisher`

### Product ecosystems
- `templates`
- `microcourse`
- `licensing`
- `leadmagnet`
- `directory`
- `community`
- `marketplace_assets`
- `miniapp`
- `extension`
- `creative_factory`
- `localization_engine`
- `experiment_runner`
- `personalization_runner`
- `pod_pack_generator`
- `licensing_stamper`

### Membership & catalog compounding
- `membership_automation`
- `membership_drip_calendar`
- `membership_issue_generator`
- `ecosystem_template_packs`
- `bundle_assembler`
- `bundle_upsell_engine`
- `product_bundle_generator`
- `sku_library_compiler`
- `pricing_listing_variant_runner`
- `variant_factory_loops`

### High-ROI v2 additions
- `prompt_library_generator`
- `vault_generator`
- `journal_workbook_generator`
- `workshop_webinar_kit`
- `lead_magnet_funnel_builder`
- `lead_magnet_snippet`
- `newsletter_excerpt`
- `youtube_script`
- `social_posts`
- `repurposing_scheduler`
- `testimonial_collector`
- `collaboration_case_study_generator`
- `analytics_import_normalizer`

### Storefront & ops
- `licensing_matrix_generator`
- `storefront_html_generator`
- `storefront_site_builder`
- `onboarding_automation`
- `dataset_to_product_pipeline`
- `support_refund_autopack`
- `pod_superpack`

### Other registered modules
- `affiliate_comparison_scale`
- `affiliate_site_mode`
- `affiliate_tables_generator`
- `brandkit_cover_factory`
- `calendar_generator`
- `marketplace_listing_optimizer`
- `micro_tool_generator`
- `price_testing_simulator`

## v2 adapter layer
Modules added in v2.x are implemented under `app/modules_v2/` and exposed to the v1 engine through wrappers in `app/modules/` (see `app/modules/v2_wrapper.py`).
This keeps the runtime **one engine**, while preserving the v2 generators **verbatim** as a separate internal package.

## Where artifacts go
- v1 modules: `data/artifacts/<module>/<topic_slug>/...` (varies per module)
- v2 adapter modules: `data/runs/<module>/<topic_slug>__<timestamp>/artifacts/<module>/...` (collision-safe)

## Quick smoke test
```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
uvicorn app.main:app --reload
# in another terminal
curl -s http://127.0.0.1:8000/v1/modules | head
curl -s -X POST http://127.0.0.1:8000/v1/modules/prompt_library_generator/generate -H "Content-Type: application/json" -d '{"topic":"Wellness coach prompts","constraints":{}}' | python -m json.tool

# Workflows
curl -s http://127.0.0.1:8000/v1/workflows | python -m json.tool
curl -s -X POST http://127.0.0.1:8000/v1/workflows/run -H "Content-Type: application/json" -d '{"name":"offer_to_storefront","topic":"AI career starter pack","constraints":{}}' | python -m json.tool

# Swarm Mode (plan → run)
curl -s -X POST http://127.0.0.1:8000/v1/swarm/plan -H "Content-Type: application/json" -d '{"goal":"Build a YouTube flywheel","topic":"Career Sanctuary","constraints":{}}' | python -m json.tool
# then paste plan_id from the response:
# curl -s -X POST http://127.0.0.1:8000/v1/swarm/run -H "Content-Type: application/json" -d '{"plan_id":123,"constraints":{}}' | python -m json.tool
```