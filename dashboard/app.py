import os, json, requests
from pathlib import Path
import streamlit as st
from app.local_services.visual_fx_bridge_client import VisualFXBridgeClient

DEFAULT_BASE = os.environ.get("EV_API_BASE", "http://127.0.0.1:18791")
API_KEY = os.environ.get("EV_API_KEY", "change-me")


def headers():
    return {"X-API-Key": API_KEY}



def safe_json(resp):
    """Best-effort JSON parsing so the dashboard never hard-crashes on non-JSON API errors."""
    try:
        return resp.json()
    except Exception:
        return {
            "_non_json": True,
            "status_code": getattr(resp, 'status_code', None),
            "content_type": getattr(resp, 'headers', {}).get('content-type', ''),
            "text": (getattr(resp, 'text', '') or '')[:4000],
        }


def fetch_modules(base_url: str) -> list:
    """Best-effort module list from the API (falls back to a known list)."""
    fallback = [
        "ebooks","youtube","etsy","newsletter","affiliate","pod","stock",
        "templates","microcourse","licensing","leadmagnet","directory","community",
        "marketplace_assets","miniapp","extension",
        "trend_miner","repurposer","offer_ladder","conversion_packager","pricing_optimizer","review_miner","support_macros",
        "calendar_generator","brandkit_cover_factory","metrics_optimizer",
        "offer_qa_gate","ab_kit_generator","inbox_faq_builder","terms_generator",
        "platform_packs","seo_engine","funnel_engine","personalization_engine",
        "creative_factory","localization_engine","experiment_runner","personalization_runner",
        # v1.0
        "programmatic_seo_generator","pod_pack_generator","licensing_stamper",
        # v1.1
        "membership_automation","ecosystem_template_packs","affiliate_site_mode","micro_tool_generator","marketplace_listing_optimizer",
        # v1.2+
        "affiliate_tables_generator","membership_issue_generator","pod_superpack","bundle_assembler",
        "licensing_matrix_generator","storefront_html_generator","onboarding_automation","dataset_to_product_pipeline","support_refund_autopack",
        # v1.4
        "storefront_site_builder","affiliate_comparison_scale",
        # v2.4 extras
        "price_testing_simulator",
        "seo_site_compiler",
        "programmatic_seo_369",
        "variant_factory_loops",
        "prompt_library_generator",
        "vault_generator",
        "journal_workbook_generator",
        "workshop_webinar_kit",
        "lead_magnet_funnel_builder",
        "funnel_compiler",
        "landing_finalizer",
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
        "youtube_script",
        "newsletter_excerpt",
        "lead_magnet_snippet",
        "product_bundle_generator",
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
        # v4.0 - Career & Job Search Tools
        "career_tools",
    ]
    try:
        r = requests.get(f"{base_url}/v1/modules", headers=headers(), timeout=30)
        if r.status_code == 200:
            data = safe_json(r)
            mods = data.get("modules")
            if isinstance(mods, list) and mods:
                return mods
    except Exception:
        pass
    return fallback



def fetch_specs(base_url: str) -> dict:
    """Best-effort module specs (schema + examples)."""
    try:
        r = requests.get(f"{base_url}/v1/modules/specs", headers=headers(), timeout=30)
        if r.status_code == 200:
            data = safe_json(r)
            specs = data.get("specs")
            if isinstance(specs, dict):
                return specs
    except Exception:
        pass
    return {}


def render_visual_outputs(meta_by_module: dict):
    thumb = meta_by_module.get("thumbnail_generator") or {}
    if thumb:
        st.markdown("#### Best Thumbnail")
        st.write({"best_thumbnail_path": thumb.get("best_thumbnail_path", ""), "ranking_method": (thumb.get("ranking_metadata") or {}).get("method", "")})
        best = thumb.get("best_thumbnail_path")
        if best and os.path.exists(best):
            st.image(best, caption="Best Thumbnail", use_container_width=True)
        ranked = thumb.get("ranked_thumbnail_paths") or []
        if ranked:
            st.markdown("#### Ranked Thumbnails")
            for pth in ranked[:6]:
                if pth and os.path.exists(pth):
                    st.image(pth, caption=Path(pth).name, use_container_width=True)
        st.caption("Prompt snippets: " + " | ".join((thumb.get("prompts_used") or [])[:2]))
        if thumb.get("preferred_final_asset"):
            st.success(f"Preferred Final Thumbnail: {thumb.get('preferred_final_asset')}")
        hj = thumb.get("handoff_jobs") or {}
        if hj:
            st.write({"thumbnail_handoff_jobs": hj})
            st.text_area("Thumbnail handoff folders", value="\n".join([str((v or {}).get("job_folder") or "") for v in hj.values() if isinstance(v, dict)]), height=80, key="thumb_handoff_paths")

    covers = meta_by_module.get("product_cover_generator") or {}
    if covers:
        st.markdown("#### Product Cover Previews")
        if covers.get("preferred_final_asset"):
            st.success(f"Preferred Final Product Cover: {covers.get('preferred_final_asset')}")
        if covers.get("handoff_jobs"):
            st.write({"product_cover_handoff_jobs": covers.get("handoff_jobs")})
            st.text_area("Product cover handoff folders", value="\n".join([str((v or {}).get("job_folder") or "") for v in (covers.get("handoff_jobs") or {}).values() if isinstance(v, dict)]), height=80, key="cover_handoff_paths")
        for pth in (covers.get("product_cover_paths") or [])[:6]:
            if pth and os.path.exists(pth):
                st.image(pth, caption=Path(pth).name, use_container_width=True)

    socials = meta_by_module.get("social_visual_generator") or {}
    if socials:
        st.markdown("#### Social Visual Previews")
        st.write({"channel": socials.get("channel", ""), "status": socials.get("status", "")})
        if socials.get("preferred_final_asset"):
            st.success(f"Preferred Final Social Visual: {socials.get('preferred_final_asset')}")
        if socials.get("handoff_jobs"):
            st.write({"social_visual_handoff_jobs": socials.get("handoff_jobs")})
            st.text_area("Social visual handoff folders", value="\n".join([str((v or {}).get("job_folder") or "") for v in (socials.get("handoff_jobs") or {}).values() if isinstance(v, dict)]), height=80, key="social_handoff_paths")
        for pth in (socials.get("social_visual_paths") or [])[:6]:
            if pth and os.path.exists(pth):
                st.image(pth, caption=Path(pth).name, use_container_width=True)


# ---- Page config + branding ----
st.set_page_config(page_title="EVIE — EmberVault Income Engine", layout="wide", page_icon="🔥")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0d0b09; }
    [data-testid="stSidebar"] { background-color: #110e0a; border-right: 1px solid #2a1f10; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255,170,50,0.05);
        border-radius: 6px 6px 0 0;
        color: #c8a060;
        font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(255,170,50,0.12) !important;
        border-bottom: 2px solid #ffaa32;
    }
    h1, h2, h3 { color: #e8dcc8 !important; }
    .stMetric label { color: #c8a060 !important; }
    .stMetric [data-testid="stMetricValue"] { color: #ffaa32 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🔥 EVIE — EmberVault Income Engine")
st.caption("RAG/Vectors · 369/Phi/Fib alignment · Product bundling · 100% local-only")

base_url = st.sidebar.text_input("API Base URL", value=DEFAULT_BASE)
api_key = st.sidebar.text_input("API Key (X-API-Key)", value=API_KEY, type="password")
API_KEY = api_key

# Sidebar status indicator
st.sidebar.divider()
try:
    _health = requests.get(f"{base_url}/health", timeout=3)
    if _health.status_code == 200:
        _hdata = safe_json(_health)
        st.sidebar.success(f"API Connected ({_hdata.get('version', '?')})", icon="✅")
        if _hdata.get("ollama") == "ok":
            st.sidebar.caption("🟢 Ollama: connected")
        elif _hdata.get("ollama") == "disabled":
            st.sidebar.caption("⚪ Ollama: disabled")
        else:
            st.sidebar.caption(f"🟡 Ollama: {_hdata.get('ollama', '?')}")
    else:
        st.sidebar.warning("API responded with non-200")
except Exception:
    st.sidebar.error("API Unreachable", icon="🚫")

st.sidebar.divider()
st.sidebar.caption("v3.2 · Studio + Swarm · 369 · Φ · Fib")

mods = fetch_modules(base_url)
specs = fetch_specs(base_url)


tabs = st.tabs(["📊 Dashboard", "📥 Ingest", "🔍 Search", "💬 RAG", "⚡ Generate", "🔥 Flywheel", "🏭 Factory", "📅 Scheduler", "📈 Runs", "📊 Metrics", "📦 Products", "🎯 Campaigns", "🧾 Evidence", "🧩 Workflows", "🧠 Swarm"])

# --- Dashboard (NEW) ---
with tabs[0]:
    st.subheader("System Overview")
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    try:
        prod_r = requests.get(f"{base_url}/v1/products", headers=headers(), timeout=10)
        prod_data = safe_json(prod_r)
        prod_count = len((prod_data or {}).get("products", [])) if prod_r.status_code == 200 else "—"
    except Exception:
        prod_count = "—"
    try:
        runs_r = requests.get(f"{base_url}/v1/runs?limit=1000", headers=headers(), timeout=10)
        runs_data = (safe_json(runs_r) or {}).get("runs", []) if runs_r.status_code == 200 else []
        runs_total = len(runs_data)
        runs_ok = sum(1 for r in runs_data if r.get("status") == "done")
        runs_err = sum(1 for r in runs_data if r.get("status") == "error")
    except Exception:
        runs_total, runs_ok, runs_err = "—", "—", "—"
    try:
        queue_r = requests.get(f"{base_url}/v1/factory/queue?limit=1000", headers=headers(), timeout=10)
        queue_items = (safe_json(queue_r) or {}).get("queue", []) if queue_r.status_code == 200 else []
        queue_pending = sum(1 for q in queue_items if q.get("status") == "queued")
    except Exception:
        queue_pending = "—"

    mcol1.metric("Products", prod_count, help="Total SKUs generated")
    mcol2.metric("Runs (done)", runs_ok, help="Completed module/offer runs")
    mcol3.metric("Runs (errors)", runs_err, help="Failed runs")
    mcol4.metric("Queue Pending", queue_pending, help="Queued factory items")
    st.divider()
    st.caption(f"**{len(mods)}** registered modules · Alignment: 369 · Φ · Fib")

    bridge_client = VisualFXBridgeClient()
    bridge_health = bridge_client.health()
    st.markdown("#### Local Visual FX Bridge")
    if bridge_health.get("ok"):
        st.success("Visual FX bridge online", icon="🧩")
        jobs_dir = (bridge_health.get("data") or {}).get("jobs_dir", "")
        st.write({"jobs_dir": jobs_dir})
        st.text_area("Copy jobs root path", value=jobs_dir, height=68, key="bridge_jobs_root_copy")
        st.caption("Open-folder hints: Windows `explorer <path>` · macOS `open <path>` · Linux `xdg-open <path>`")

        recent = bridge_client.recent_jobs(limit=8)
        jobs = recent.get("jobs") if recent.get("ok") else []
        if jobs:
            st.dataframe([
                {
                    "job_id": j.get("job_id"),
                    "job_type": j.get("job_type"),
                    "tool": j.get("tool_name"),
                    "status": j.get("status"),
                    "outputs_detected": j.get("detected_outputs_count", 0),
                    "updated_at": j.get("updated_at"),
                    "job_folder": j.get("job_folder"),
                    "output_folder": j.get("output_folder"),
                }
                for j in jobs
            ], use_container_width=True)
            first = jobs[0]
            st.text_area("Copy latest handoff folder", value=first.get("job_folder", ""), height=68, key="bridge_latest_handoff_copy")
            st.text_area("Copy latest output folder", value=first.get("output_folder", ""), height=68, key="bridge_latest_output_copy")
    else:
        st.warning("Visual FX bridge offline (visual handoff will degrade gracefully).")

    with st.expander("Readiness + Smoke Test Commands"):
        st.code("python tools/check_readiness.py", language="bash")
        st.code("python tools/run_smoke_tests.py", language="bash")


# --- Ingest ---
with tabs[1]:
    st.subheader("Ingest into Vault")
    ingest_upload = st.file_uploader("Upload file (pdf/txt/md/image/audio/video)", type=None, key="ingest_upload")
    ingest_meta = st.text_area("Metadata JSON (optional)", value="{}", key="ingest_meta")
    if st.button("Ingest File", disabled=(ingest_upload is None), key="btn_ingest_file"):
        try:
            files = {"file": (ingest_upload.name, ingest_upload.getvalue())}
            with st.spinner("Ingesting file..."):
                r = requests.post(f"{base_url}/v1/ingest/file", headers=headers(), files=files, data={"metadata_json": ingest_meta}, timeout=300)
            if r.status_code == 200:
                st.success("File ingested successfully!")
            else:
                st.warning(f"Status {r.status_code}")
            st.json(safe_json(r))
        except Exception as e:
            st.error(str(e))

    st.divider()
    ingest_title = st.text_input("Quick text title", value="Note", key="ingest_title")
    ingest_text = st.text_area("Quick text", value="", key="ingest_text")
    if st.button("Ingest Text", key="btn_ingest_text"):
        with st.spinner("Ingesting text..."):
            r = requests.post(f"{base_url}/v1/ingest/text", headers=headers(), json={"title": ingest_title, "text": ingest_text, "metadata": json.loads(ingest_meta or "{}")}, timeout=120)
        st.json(safe_json(r))

# --- Search ---
with tabs[2]:
    st.subheader("Hybrid Search (Vector + optional SQLite FTS)")
    search_query = st.text_input("Query", value="what did I ingest?", key="search_query")
    search_k = st.slider("Top K", 1, 20, 8, key="search_k")
    search_mode = st.selectbox("Mode", ["hybrid", "vector", "fts"], index=0, key="search_mode")
    if st.button("Search", key="btn_search"):
        with st.spinner("Searching..."):
            r = requests.post(
                f"{base_url}/v1/search",
                headers=headers(),
                json={"query": search_query, "top_k": search_k, "mode": search_mode, "fts_k": 10},
                timeout=120,
            )
        data = safe_json(r)
        results = data.get("results") or data.get("hits") or []
        if isinstance(results, list) and results:
            for i, hit in enumerate(results):
                with st.expander(f"Result {i+1} — score: {hit.get('score', 0):.3f} (base: {hit.get('score_base', 0):.3f}, harmonic: {hit.get('score_harmonic', 0):.3f})"):
                    st.text(hit.get("text", "")[:500])
                    st.caption(f"chunk_id={hit.get('chunk_id')} · doc_id={hit.get('doc_id')} · key={hit.get('canonical_key')}")
            if data.get("fts_hits"):
                st.divider()
                st.markdown("### FTS hits")
                st.json(data.get("fts_hits"))
        else:
            st.json(data)

# --- RAG ---
with tabs[3]:
    st.subheader("RAG Answer")
    rag_question = st.text_area("Question", value="Summarize the most important points from my vault.", key="rag_question")
    rag_k = st.slider("Top K (context chunks)", 1, 20, 8, key="rag_k")
    if st.button("Answer", key="btn_rag"):
        with st.spinner("Generating answer from vault context..."):
            r = requests.post(f"{base_url}/v1/rag/answer", headers=headers(), json={"question": rag_question, "top_k": rag_k}, timeout=300)
        data = safe_json(r)
        answer = data.get("answer", "")
        if answer:
            st.markdown("### Answer")
            st.markdown(answer)
            st.divider()
            st.caption("Sources:")
            st.json(data.get("sources", []))
        else:
            st.json(data)

# --- Modules ---
with tabs[4]:
    st.subheader("Generate single asset")
    gen_module = st.selectbox("Module", mods, key="gen_module")
    gen_topic = st.text_input("Topic", value="AI career sanctuary tips", key="gen_topic")

    spec = specs.get(gen_module) or {}
    if spec:
        st.caption(spec.get("description",""))
        spec_cols = st.columns(2)
        if spec_cols[0].button("Load example constraints", key="btn_load_example"):
            ex = spec.get("example_constraints") or {}
            st.session_state["constraints_json"] = json.dumps(ex, indent=2)
        if spec_cols[1].button("Show JSON schema", key="btn_show_schema"):
            st.json(spec.get("input_schema") or {})

    if "constraints_json" not in st.session_state:
        st.session_state["constraints_json"] = "{}"

    gen_constraints = st.text_area("Constraints JSON (optional)", value=st.session_state["constraints_json"], key="gen_constraints_area")
    st.session_state["constraints_json"] = gen_constraints

    gen_async = st.checkbox("Async (enqueue in scheduler)", value=False, key="gen_async")
    if st.button("Generate", key="btn_generate"):
        payload = {"topic": gen_topic, "constraints": json.loads(gen_constraints or "{}"), "async_run": bool(gen_async)}
        with st.spinner(f"Running {gen_module}..."):
            r = requests.post(f"{base_url}/v1/modules/{gen_module}/generate", headers=headers(), json=payload, timeout=600)
        if r.status_code == 200:
            st.success(f"✅ {gen_module} completed!")
        else:
            st.error(f"Status {r.status_code}")
        st.json(safe_json(r))

# --- Flywheel ---
with tabs[5]:
    st.subheader("Build an Offer Bundle (auto product + zip)")
    offer_topic = st.text_input("Offer topic", value="AI job-search starter pack", key="offer_topic")
    offer_modules = st.multiselect("Modules to include", mods, default=[m for m in ["ebooks","youtube","newsletter","stock","templates","leadmagnet","repurposer","conversion_packager","programmatic_seo_generator","pod_pack_generator"] if m in mods], key="offer_modules")

    offer_price = st.number_input("Price (cents)", min_value=0, value=2900, step=100, key="offer_price")
    if st.button("Build Offer Bundle", key="btn_build_offer"):
        with st.spinner(f"Building offer with {len(offer_modules)} modules... This may take several minutes."):
            r = requests.post(f"{base_url}/v1/flywheel/offer", headers=headers(), json={"topic": offer_topic, "modules": offer_modules, "price_cents": int(offer_price)}, timeout=900)
        data = safe_json(r)
        if data.get("sku"):
            st.success(f"✅ Offer built! SKU: **{data.get('sku')}** · Version: **{data.get('version')}**")
            st.caption(f"Bundle: `{data.get('bundle_zip')}`")
            st.caption(f"Gumroad-ready: `{data.get('gumroad_dir')}`")
        st.json(data)


# --- Factory ---
with tabs[6]:
    st.subheader("Product Factory (9-pack queue)")
    st.caption("Seeds a queue and can auto-schedule builds on Fibonacci days. Local-only.")

    factory_focus = st.text_input("Factory focus", value="Career Sanctuary", key="factory_focus")
    factory_niches = st.text_input("Niches (comma-separated)", value="resume, interviews, networking", key="factory_niches")
    factory_top_n = st.slider("How many queue items", 3, 21, 9, key="factory_top_n")
    factory_priority = st.slider("Priority", 0, 9, 0, key="factory_priority")
    factory_fib = st.checkbox("Schedule builds (Fib days)", value=True, key="factory_fib")
    if st.button("Seed Queue", key="btn_seed_queue"):
        payload = {"focus": factory_focus, "niches": [x.strip() for x in factory_niches.split(',') if x.strip()], "top_n": int(factory_top_n), "priority": int(factory_priority), "schedule_fib": bool(factory_fib)}
        with st.spinner("Seeding factory queue..."):
            r = requests.post(f"{base_url}/v1/factory/seed", headers=headers(), json=payload, timeout=120)
        st.json(safe_json(r))

    st.divider()
    if st.button("List Queue", key="btn_list_queue"):
        r = requests.get(f"{base_url}/v1/factory/queue?limit=100", headers=headers(), timeout=120)
        st.json(safe_json(r))

    st.divider()
    factory_default_price = st.number_input("Default price cents (if not set)", min_value=0, value=2900, step=100, key="factory_default_price")
    if st.button("Run Next Queue Item (Build Offer)", key="btn_run_next"):
        with st.spinner("Building next queue item..."):
            r = requests.post(f"{base_url}/v1/factory/run_next", headers=headers(), json={"default_price_cents": int(factory_default_price)}, timeout=900)
        st.json(safe_json(r))

    st.divider()
    if st.button("Export Catalog (JSON+CSV)", key="btn_export_catalog"):
        with st.spinner("Exporting..."):
            r = requests.post(f"{base_url}/v1/factory/export_catalog", headers=headers(), timeout=120)
        st.json(safe_json(r))

# --- Scheduler ---
with tabs[7]:
    st.subheader("Scheduler")
    st.caption("View queued tasks and run due tasks now (local-only). For continuous automation, run: `python cli.py worker-loop`")

    sched_status = st.selectbox("Filter status", ["", "queued", "running", "done", "error"], index=0, key="sched_status")
    if st.button("Refresh Tasks", key="btn_refresh_tasks"):
        url = f"{base_url}/v1/scheduler/tasks?limit=50"
        if sched_status:
            url += f"&status={sched_status}"
        r = requests.get(url, headers=headers(), timeout=120)
        st.json(safe_json(r))

    st.divider()
    sched_max = st.slider("Run due tasks (batch size)", 1, 10, 3, key="sched_max")
    if st.button("Run Due Now", key="btn_run_due"):
        with st.spinner("Running due tasks..."):
            r = requests.post(f"{base_url}/v1/scheduler/run_due", headers=headers(), json={"max_tasks": int(sched_max)}, timeout=900)
        st.json(safe_json(r))

# --- Runs ---
with tabs[8]:
    st.subheader("Runs")
    st.caption("Run history for modules/offers/factory builds (local-only)")
    runs_filter_status = st.selectbox("Filter run status", ["", "running", "done", "error"], index=0, key="runs_filter_status")
    runs_limit = st.slider("Limit", 10, 200, 50, key="runs_limit")
    if st.button("Refresh Runs", key="btn_refresh_runs"):
        url = f"{base_url}/v1/runs?limit={int(runs_limit)}"
        if runs_filter_status:
            url += f"&status={runs_filter_status}"
        rr = requests.get(url, headers=headers(), timeout=120)
        data = safe_json(rr)
        runs_list = data.get("runs", [])
        if isinstance(runs_list, list) and runs_list:
            for run in runs_list:
                status_icon = {"done": "✅", "running": "🔄", "error": "❌"}.get(run.get("status"), "⏳")
                with st.expander(f"{status_icon} Run #{run.get('run_id', '?')} — {run.get('topic', 'N/A')} ({run.get('status')})"):
                    col_a, col_b, col_c = st.columns(3)
                    col_a.caption(f"**Type:** {run.get('run_type')}")
                    col_b.caption(f"**Module:** {run.get('module')}")
                    col_c.caption(f"**Duration:** {run.get('duration_ms', '—')}ms")
                    if run.get("error"):
                        st.error(run["error"])
        else:
            st.json(data)

    st.divider()
    run_detail_id = st.text_input("Run ID (for details)", value="", key="run_detail_id")
    if st.button("Get Run Details", key="btn_run_details") and run_detail_id.strip():
        rr = requests.get(f"{base_url}/v1/runs/{run_detail_id.strip()}", headers=headers(), timeout=120)
        st.json(safe_json(rr))

# --- Metrics ---
with tabs[9]:
    st.subheader("Metrics Import + Optimizer (local)")
    st.caption("Upload exports (CSV) from your storefront, email platform, YouTube analytics, etc. No network calls.")

    metrics_source = st.text_input("Source label (optional)", value="gumroad/youtube/newsletter", key="metrics_source")
    metrics_upload = st.file_uploader("Upload a metrics CSV", type=["csv"], key="metrics_upload")
    if st.button("Upload Metrics CSV", key="btn_upload_metrics") and metrics_upload is not None:
        files = {"file": (metrics_upload.name, metrics_upload.getvalue(), "text/csv")}
        data = {"source": metrics_source}
        with st.spinner("Importing metrics..."):
            r = requests.post(f"{base_url}/v1/metrics/import", headers=headers(), files=files, data=data, timeout=300)
        st.json(safe_json(r))

    st.divider()
    metrics_colA, metrics_colB = st.columns(2)
    with metrics_colA:
        if st.button("List recent metric runs", key="btn_list_metric_runs"):
            r = requests.get(f"{base_url}/v1/metrics/runs?limit=25", headers=headers(), timeout=120)
            st.json(safe_json(r))
    with metrics_colB:
        metrics_run_id = st.number_input("Run ID to analyze", min_value=0, value=0, step=1, key="metrics_run_id")
        metrics_topic = st.text_input("Report topic label", value="My Storefront Metrics", key="metrics_topic")
        if st.button("Analyze", key="btn_analyze_metrics"):
            payload = {"run_id": int(metrics_run_id) if int(metrics_run_id) > 0 else None, "topic": metrics_topic}
            with st.spinner("Analyzing metrics..."):
                r = requests.post(f"{base_url}/v1/metrics/analyze", headers=headers(), json=payload, timeout=300)
            st.json(safe_json(r))

# --- Products ---
with tabs[10]:
    st.subheader("Products")
    if st.button("Refresh", key="btn_refresh_products"):
        r = requests.get(f"{base_url}/v1/products", headers=headers(), timeout=120)
        data = safe_json(r)
        products = data.get("products", [])
        if isinstance(products, list) and products:
            for p in products:
                status_icon = {"draft": "📝", "published": "🟢", "archived": "📁"}.get(p.get("status"), "❓")
                with st.expander(f"{status_icon} {p.get('name', 'Untitled')} — {p.get('sku', 'N/A')}"):
                    pc1, pc2, pc3 = st.columns(3)
                    pc1.metric("Price", f"${p.get('price_cents', 0)/100:.2f}")
                    pc2.caption(f"**Module:** {p.get('module')}")
                    pc3.caption(f"**Version:** {p.get('current_version', '—')}")
                    pc1.caption(f"**Status:** {p.get('status')}")
        else:
            st.json(data)

# --- Campaigns ---
with tabs[11]:
    st.subheader("Campaigns (Studio Mode)")
    st.caption("Local-first campaign registry. Use this to organize niches, audiences, and platforms.")

    c_name = st.text_input("Campaign name", value="New Campaign", key="c_name")
    c_niche = st.text_input("Niche", value="", key="c_niche")
    c_audience = st.text_input("Audience", value="", key="c_audience")
    c_promise = st.text_input("Promise", value="", key="c_promise")
    c_platforms = st.text_area("Platforms JSON", value='{"youtube":true,"newsletter":true,"gumroad":true}', key="c_platforms")
    if st.button("Create Campaign", key="btn_create_campaign"):
        payload = {
            "name": c_name,
            "niche": c_niche,
            "audience": c_audience,
            "promise": c_promise,
            "platforms": json.loads(c_platforms or "{}"),
            "status": "active",
            "metadata": {},
        }
        r = requests.post(f"{base_url}/v1/campaigns/create", headers=headers(), json=payload, timeout=60)
        st.json(safe_json(r))

    st.divider()
    if st.button("Refresh Campaigns", key="btn_refresh_campaigns"):
        r = requests.get(f"{base_url}/v1/campaigns?limit=50", headers=headers(), timeout=60)
        st.json(safe_json(r))


# --- Evidence ---
with tabs[12]:
    st.subheader("Evidence (Reconnect layer)")
    st.caption("Attach notes/links/files to a campaign, session, or product. Searchable via FTS.")

    ev_campaign_id = st.number_input("Campaign ID (optional)", min_value=0, value=0, step=1, key="ev_campaign_id")
    ev_session_id = st.number_input("Session ID (optional)", min_value=0, value=0, step=1, key="ev_session_id")
    ev_product_id = st.number_input("Product ID (optional)", min_value=0, value=0, step=1, key="ev_product_id")
    ev_kind = st.selectbox("Kind", ["note", "link", "file"], index=0, key="ev_kind")
    ev_title = st.text_input("Title", value="", key="ev_title")
    ev_url = st.text_input("URL (if link)", value="", key="ev_url")
    ev_content = st.text_area("Content (if note)", value="", key="ev_content")
    ev_tags = st.text_input("Tags (comma-separated)", value="research,proof", key="ev_tags")
    ev_sensitive = st.checkbox("Mark sensitive (will be redacted in exports)", value=False, key="ev_sensitive")

    if st.button("Create Evidence", key="btn_create_evidence"):
        payload = {
            "campaign_id": int(ev_campaign_id) if int(ev_campaign_id) > 0 else None,
            "session_id": int(ev_session_id) if int(ev_session_id) > 0 else None,
            "product_id": int(ev_product_id) if int(ev_product_id) > 0 else None,
            "kind": ev_kind,
            "title": ev_title,
            "url": ev_url or None,
            "content": ev_content or None,
            "file_path": None,
            "tags": [t.strip() for t in (ev_tags or "").split(",") if t.strip()],
            "sensitive": bool(ev_sensitive),
        }
        r = requests.post(f"{base_url}/v1/evidence/create", headers=headers(), json=payload, timeout=60)
        st.json(safe_json(r))

    st.divider()
    if st.button("List Evidence", key="btn_list_evidence"):
        qs = []
        if int(ev_campaign_id) > 0:
            qs.append(f"campaign_id={int(ev_campaign_id)}")
        if int(ev_session_id) > 0:
            qs.append(f"session_id={int(ev_session_id)}")
        if int(ev_product_id) > 0:
            qs.append(f"product_id={int(ev_product_id)}")
        url = f"{base_url}/v1/evidence?limit=50" + ("&" + "&".join(qs) if qs else "")
        r = requests.get(url, headers=headers(), timeout=60)
        st.json(safe_json(r))


# --- Workflows ---
with tabs[13]:
    st.subheader("Workflows (TIEKAT-style recipes)")
    st.caption("List and run workflows (multi-module recipes) with a single call.")

    wf_catalog = {}
    if st.button("Refresh Workflows", key="btn_list_workflows"):
        r = requests.get(f"{base_url}/v1/workflows", headers=headers(), timeout=60)
        wf_data = safe_json(r)
        st.json(wf_data)
        wf_catalog = {w.get("name"): w for w in (wf_data.get("workflows") or []) if isinstance(w, dict)}
    else:
        try:
            _r = requests.get(f"{base_url}/v1/workflows", headers=headers(), timeout=30)
            _d = safe_json(_r)
            wf_catalog = {w.get("name"): w for w in (_d.get("workflows") or []) if isinstance(w, dict)}
        except Exception:
            wf_catalog = {}

    st.divider()
    wf_name = st.text_input("Workflow name", value="offer_to_storefront", key="wf_name")
    wf_topic = st.text_input("Workflow topic", value="My next offer", key="wf_topic")
    wf_constraints = st.text_area("Constraints JSON", value="{}", key="wf_constraints")
    wf_dry = st.checkbox("Dry run", value=False, key="wf_dry")
    if st.button("Run Workflow", key="btn_run_workflow"):
        try:
            parsed = json.loads(wf_constraints or "{}")
        except Exception as e:
            st.error(f"Constraints JSON is invalid: {e}")
            parsed = None
        if parsed is not None:
            payload = {"topic": wf_topic, "constraints": parsed, "dry_run": bool(wf_dry)}
            r = requests.post(f"{base_url}/v1/workflows/{wf_name}/run", headers=headers(), json=payload, timeout=900)
            st.json(safe_json(r))

    st.divider()
    st.markdown("### 📈 Trend → Money Publish")
    st.caption("Focused runner for `trend_to_money_publish` (strategy modules + money workflow + optional publish workflow).")
    ttm_topic = st.text_input("Trend workflow topic", value="AI Creator Playbooks", key="ttm_topic")
    ttm_keywords = st.text_input("Keywords (comma separated)", value="ai creator tools, micro products", key="ttm_keywords")
    tc1, tc2, tc3 = st.columns(3)
    ttm_cross = tc1.checkbox("Include cross pollination", value=True, key="ttm_cross")
    ttm_preds = tc2.checkbox("Create predictions", value=True, key="ttm_preds")
    ttm_publish = tc3.checkbox("Run publish workflow", value=False, key="ttm_publish")
    tc4, tc5, tc6, tc7 = st.columns(4)
    ttm_audio = tc4.checkbox("Include audio", value=False, key="ttm_audio")
    ttm_video = tc5.checkbox("Include video", value=False, key="ttm_video")
    ttm_auto = tc6.checkbox("Auto publish", value=False, key="ttm_auto")
    ttm_dry = tc7.checkbox("Dry run", value=True, key="ttm_dry")
    tc8, tc9 = st.columns(2)
    ttm_thread = tc8.checkbox("Include thread bomber", value=False, key="ttm_thread_bomber")
    ttm_short = tc9.checkbox("Include short-form pack", value=False, key="ttm_short_form")

    if st.button("Run trend_to_money_publish", key="btn_run_ttm"):
        constraints = {
            "keywords": [k.strip() for k in (ttm_keywords or "").split(",") if k.strip()],
            "include_cross_pollination": bool(ttm_cross),
            "create_predictions": bool(ttm_preds),
            "include_audio": bool(ttm_audio),
            "include_video": bool(ttm_video),
            "run_publish_workflow": bool(ttm_publish),
            "include_thread_bomber": bool(ttm_thread),
            "include_short_form_pack": bool(ttm_short),
            "auto_publish": bool(ttm_auto),
            "dry_run": bool(ttm_dry),
        }
        r = requests.post(
            f"{base_url}/v1/workflows/trend_to_money_publish/run",
            headers=headers(),
            json={"topic": ttm_topic, "constraints": constraints, "dry_run": False},
            timeout=1800,
        )
        st.json(safe_json(r))

    st.divider()
    st.markdown("### 📚 Vault → Lesson Pack")
    st.caption("Focused runner for `vault_to_lesson_pack` with optional audio/video generation.")

    lp_preset = st.selectbox(
        "Preset",
        ["Basic Lesson Pack", "Lesson Pack + Audio", "Lesson Pack + Audio + Video"],
        index=0,
        key="lp_preset",
    )

    lp_topic = st.text_input("Lesson topic", value="Sovereign Body Reset", key="lp_topic")
    lp_context = st.text_area("Optional context", value="", key="lp_context")
    lp_artifacts_raw = st.text_area(
        "Optional artifact paths (one per line)",
        value="",
        key="lp_artifacts_raw",
        help="Optional prior artifacts from data/ paths.",
    )
    lpc1, lpc2 = st.columns(2)
    preset_audio = lp_preset in {"Lesson Pack + Audio", "Lesson Pack + Audio + Video"}
    preset_video = lp_preset in {"Lesson Pack + Audio + Video"}
    lp_include_audio = lpc1.checkbox("Include audio", value=preset_audio, key="lp_include_audio")
    lp_include_video = lpc2.checkbox("Include video", value=preset_video, key="lp_include_video")

    if st.button("Run vault_to_lesson_pack", key="btn_run_lesson_pack"):
        artifact_paths = [ln.strip() for ln in (lp_artifacts_raw or "").splitlines() if ln.strip()]
        constraints = {
            "include_audio": bool(lp_include_audio),
            "include_video": bool(lp_include_video),
        }
        if lp_context.strip():
            constraints["context"] = lp_context.strip()
        if artifact_paths:
            constraints["artifact_paths"] = artifact_paths

        with st.spinner("Running vault_to_lesson_pack..."):
            r = requests.post(
                f"{base_url}/v1/workflows/vault_to_lesson_pack/run",
                headers=headers(),
                json={"topic": lp_topic, "constraints": constraints, "dry_run": False},
                timeout=1800,
            )
        data = safe_json(r)

        status = str(data.get("status") or ("error" if r.status_code >= 400 else "done")).lower()
        if status == "done":
            st.success(f"Workflow status: {status}")
        elif status == "partial":
            st.warning(f"Workflow status: {status}")
        else:
            st.error(f"Workflow status: {status}")

        steps = data.get("steps") or []
        if isinstance(steps, list) and steps:
            render_visual_outputs(by_module)

            st.markdown("#### Step Results")
            rows = []
            artifact_groups = {}
            for s in steps:
                meta = s.get("metadata") or {}
                step_msg = meta.get("error") or (meta.get("v2_summary") or {}).get("error") or s.get("reason") or ""
                mod = s.get("module") or "unknown"
                artifact_groups[mod] = list(s.get("artifact_paths") or [])
                rows.append({
                    "step": s.get("step"),
                    "module": s.get("module"),
                    "status": s.get("status", "done"),
                    "artifacts": len(s.get("artifact_paths") or []),
                    "message": step_msg,
                })
            st.dataframe(rows, use_container_width=True)

            all_artifacts = []
            for _m, paths in artifact_groups.items():
                all_artifacts.extend(paths)
            if all_artifacts:
                ext_priority = {".md": 1, ".pptx": 2, ".png": 3, ".html": 4, ".json": 5, ".mp3": 6, ".mp4": 7, ".pdf": 8}
                top_outputs = sorted(
                    all_artifacts,
                    key=lambda p: (ext_priority.get(os.path.splitext(p)[1].lower(), 99), p),
                )[:8]
                st.markdown("#### Top Outputs")
                for p in top_outputs:
                    st.markdown(f"- `{p}`")

                st.markdown("#### Copy All Artifact Paths")
                st.text_area(
                    "Artifact paths",
                    value="\n".join(all_artifacts),
                    height=140,
                    key="lp_all_artifacts_copy",
                )

            for s in steps:
                with st.expander(f"Step {s.get('step')} · {s.get('module')} · {s.get('status', 'done')}"):
                    if s.get("artifact_paths"):
                        st.markdown("**Artifacts**")
                        st.code("\n".join(s.get("artifact_paths") or []), language="text")
                        st.text_area(
                            f"Copy paths · {s.get('module')}",
                            value="\n".join(s.get("artifact_paths") or []),
                            height=80,
                            key=f"lp_copy_{s.get('step')}_{s.get('module')}",
                        )
                    meta = s.get("metadata") or {}
                    err = meta.get("error") or (meta.get("v2_summary") or {}).get("error")
                    if err:
                        st.warning(err)
                    st.json(s)
        else:
            st.json(data)

    st.divider()
    st.markdown("### 💸 Vault → Money Pack")
    st.caption("Run `vault_to_money_pack` to generate lesson assets plus product, sales, and distribution outputs.")

    mp_topic = st.text_input("Money pack topic", value="Sovereign Body Reset", key="mp_topic")
    mp_context = st.text_area("Optional money-pack context", value="", key="mp_context")
    mpc1, mpc2 = st.columns(2)
    mp_include_audio = mpc1.checkbox("Include audio", value=False, key="mp_include_audio")
    mp_include_video = mpc2.checkbox("Include video", value=False, key="mp_include_video")
    mpc3, mpc4, mpc5 = st.columns(3)
    mp_generate_images = mpc3.checkbox("Generate images", value=False, key="mp_generate_images")
    mp_image_style = mpc4.selectbox("Image style", ["cinematic", "product", "social", "minimal", "cosmic"], index=0, key="mp_image_style")
    mp_num_images = mpc5.number_input("# Images", min_value=1, max_value=8, value=3, step=1, key="mp_num_images")
    mpc6, mpc7, mpc8 = st.columns(3)
    mp_generate_thumbs = mpc6.checkbox("Generate thumbnails", value=False, key="mp_generate_thumbnails")
    mp_generate_covers = mpc7.checkbox("Generate product covers", value=False, key="mp_generate_product_covers")
    mp_generate_social = mpc8.checkbox("Generate social visuals", value=False, key="mp_generate_social_visuals")

    if st.button("Run vault_to_money_pack", key="btn_run_money_pack"):
        mp_constraints = {
            "include_audio": bool(mp_include_audio),
            "include_video": bool(mp_include_video),
            "generate_images": bool(mp_generate_images),
            "image_style": mp_image_style,
            "num_images": int(mp_num_images),
            "generate_thumbnails": bool(mp_generate_thumbs),
            "generate_product_covers": bool(mp_generate_covers),
            "generate_social_visuals": bool(mp_generate_social),
        }
        if mp_context.strip():
            mp_constraints["context"] = mp_context.strip()

        with st.spinner("Running vault_to_money_pack..."):
            r = requests.post(
                f"{base_url}/v1/workflows/vault_to_money_pack/run",
                headers=headers(),
                json={"topic": mp_topic, "constraints": mp_constraints, "dry_run": False},
                timeout=1800,
            )
        data = safe_json(r)
        status = str(data.get("status") or ("error" if r.status_code >= 400 else "done")).lower()
        if status == "done":
            st.success(f"Workflow status: {status}")
        elif status == "partial":
            st.warning(f"Workflow status: {status}")
        else:
            st.error(f"Workflow status: {status}")

        steps = data.get("steps") or []
        if isinstance(steps, list) and steps:
            by_module = {s.get("module"): (s.get("metadata") or {}) for s in steps if isinstance(s, dict)}
            product = by_module.get("product_packager") or {}
            hooks = by_module.get("hooks_generator") or {}
            sales = by_module.get("sales_copy_generator") or {}
            dist = by_module.get("distribution_generator") or {}

            st.markdown("#### Product Info")
            st.write({
                "product_name": product.get("product_name"),
                "product_description": product.get("product_description"),
                "bundle_contents": product.get("bundle_contents"),
                "price_suggestion": product.get("price_suggestion"),
            })

            st.markdown("#### Hooks")
            for h in (hooks.get("hooks") or [])[:10]:
                st.markdown(f"- {h}")

            st.markdown("#### YouTube")
            st.code(
                f"Title: {dist.get('youtube_title', '')}\n\nDescription:\n{dist.get('youtube_description', '')}",
                language="text",
            )

            st.markdown("#### Sales Copy")
            st.code(
                f"Headline: {sales.get('headline', '')}\n\n{sales.get('full_description', '')}\n\nCTA: {sales.get('call_to_action', '')}",
                language="text",
            )

            all_artifacts = []
            for s in steps:
                all_artifacts.extend(s.get("artifact_paths") or [])
            if all_artifacts:
                st.markdown("#### Artifacts")
                st.text_area("Copy artifact paths", value="\n".join(all_artifacts), height=140, key="mp_artifacts_copy")

            st.markdown("#### Step Results")
            st.dataframe([
                {
                    "step": s.get("step"),
                    "module": s.get("module"),
                    "status": s.get("status", "done"),
                    "artifacts": len(s.get("artifact_paths") or []),
                    "message": (s.get("metadata") or {}).get("error") or ((s.get("metadata") or {}).get("v2_summary") or {}).get("error") or "",
                }
                for s in steps
            ], use_container_width=True)
        else:
            st.json(data)

    st.divider()
    st.markdown("### 🚀 Money → Publish")
    st.caption("Run `vault_to_money_publish` with safe publish controls.")

    pub_topic = st.text_input("Publish topic", value="Sovereign Body Reset", key="pub_topic")
    pubc1, pubc2 = st.columns(2)
    pub_include_audio = pubc1.checkbox("Include audio", value=False, key="pub_include_audio")
    pub_include_video = pubc2.checkbox("Include video", value=False, key="pub_include_video")
    pubc10, pubc11, pubc12 = st.columns(3)
    pub_generate_images = pubc10.checkbox("Generate images", value=False, key="pub_generate_images")
    pub_image_style = pubc11.selectbox("Image style", ["cinematic", "product", "social", "minimal", "cosmic"], index=0, key="pub_image_style")
    pub_num_images = pubc12.number_input("# Images", min_value=1, max_value=8, value=3, step=1, key="pub_num_images")
    pubc13, pubc14, pubc15 = st.columns(3)
    pub_generate_thumbs = pubc13.checkbox("Generate thumbnails", value=False, key="pub_generate_thumbnails")
    pub_generate_covers = pubc14.checkbox("Generate product covers", value=False, key="pub_generate_product_covers")
    pub_generate_social_visuals = pubc15.checkbox("Generate social visuals", value=False, key="pub_generate_social_visuals")
    pubc3, pubc4 = st.columns(2)
    pub_auto = pubc3.checkbox("Auto publish", value=False, key="pub_auto_publish")
    pub_dry = pubc4.checkbox("Dry run", value=True, key="pub_dry_run")
    pubc5, pubc6 = st.columns(2)
    pub_to_gum = pubc5.checkbox("Publish to Gumroad", value=True, key="pub_to_gumroad")
    pub_to_yt = pubc6.checkbox("Publish to YouTube", value=True, key="pub_to_youtube")
    pubc7, pubc8, pubc9 = st.columns(3)
    pub_social = pubc7.checkbox("Export social pack", value=True, key="pub_export_social")
    pub_news = pubc8.checkbox("Export newsletter pack", value=True, key="pub_export_news")
    pub_payhip = pubc9.checkbox("Export Payhip pack", value=True, key="pub_export_payhip")
    pubc16, pubc17 = st.columns(2)
    pub_thread = pubc16.checkbox("Include thread bomber", value=False, key="pub_include_thread_bomber")
    pub_short = pubc17.checkbox("Include short-form pack", value=False, key="pub_include_short_form_pack")

    if st.button("Run vault_to_money_publish", key="btn_run_money_publish"):
        constraints = {
            "include_audio": bool(pub_include_audio),
            "include_video": bool(pub_include_video),
            "generate_images": bool(pub_generate_images),
            "image_style": pub_image_style,
            "num_images": int(pub_num_images),
            "generate_thumbnails": bool(pub_generate_thumbs),
            "generate_product_covers": bool(pub_generate_covers),
            "generate_social_visuals": bool(pub_generate_social_visuals),
            "auto_publish": bool(pub_auto),
            "dry_run": bool(pub_dry),
            "publish_to_gumroad": bool(pub_to_gum),
            "publish_to_youtube": bool(pub_to_yt),
            "export_social_pack": bool(pub_social),
            "export_newsletter_pack": bool(pub_news),
            "export_payhip_pack": bool(pub_payhip),
            "include_thread_bomber": bool(pub_thread),
            "include_short_form_pack": bool(pub_short),
        }
        with st.spinner("Running vault_to_money_publish..."):
            r = requests.post(
                f"{base_url}/v1/workflows/vault_to_money_publish/run",
                headers=headers(),
                json={"topic": pub_topic, "constraints": constraints, "dry_run": False},
                timeout=1800,
            )
        data = safe_json(r)
        status = str(data.get("status") or ("error" if r.status_code >= 400 else "done")).lower()
        if status == "done":
            st.success(f"Workflow status: {status}")
        elif status == "partial":
            st.warning(f"Workflow status: {status}")
        else:
            st.error(f"Workflow status: {status}")

        steps = data.get("steps") or []
        if isinstance(steps, list) and steps:
            meta_by_module = {s.get("module"): (s.get("metadata") or {}) for s in steps if isinstance(s, dict)}
            gum = meta_by_module.get("gumroad_publisher") or {}
            yt = meta_by_module.get("youtube_publisher") or {}
            exporter = meta_by_module.get("content_exporter") or {}
            newsletter = meta_by_module.get("newsletter_packager") or {}
            social = meta_by_module.get("social_launch_packager") or {}

            st.markdown("#### Real/Simulated Publish Results")
            st.write({
                "export_folder": exporter.get("export_folder", ""),
                "preferred_final_assets": exporter.get("preferred_final_assets", {}),
                "gumroad_status": gum.get("status", "not_run"),
                "youtube_status": yt.get("status", "not_run"),
                "gumroad_product_link": gum.get("product_url", ""),
                "youtube_video_link": yt.get("video_url", ""),
            })

            st.info("Exported content packs are always manual-ready. Simulated publish occurs with Dry run. Real publish only occurs with Auto publish + valid credentials.")

            st.markdown("#### Exported Content")
            packs = exporter.get("packs") or {}
            if packs:
                st.write(packs)
                try:
                    if packs.get("newsletter") and os.path.exists(packs.get("newsletter")):
                        st.markdown("##### Newsletter")
                        st.json(json.loads(Path(packs.get("newsletter")).read_text(encoding="utf-8")))
                    elif newsletter:
                        st.markdown("##### Newsletter")
                        st.json(newsletter)

                    if packs.get("social") and os.path.exists(packs.get("social")):
                        st.markdown("##### Social")
                        st.json(json.loads(Path(packs.get("social")).read_text(encoding="utf-8")))
                    elif social:
                        st.markdown("##### Social")
                        st.json(social)

                    if packs.get("payhip") and os.path.exists(packs.get("payhip")):
                        st.markdown("##### Payhip")
                        st.json(json.loads(Path(packs.get("payhip")).read_text(encoding="utf-8")))
                except Exception:
                    pass
            else:
                st.write({"newsletter": newsletter, "social": social})

            img_meta = meta_by_module.get("image_generator_v2") or {}
            if img_meta:
                st.markdown("#### Generated Images")
                st.write({"status": img_meta.get("status"), "prompts": img_meta.get("prompts_used", [])[:3]})
                for pth in (img_meta.get("image_paths") or [])[:6]:
                    if pth and os.path.exists(pth):
                        st.image(pth, caption=Path(pth).name, use_container_width=True)

            render_visual_outputs(meta_by_module)
            if meta_by_module.get("thread_bomber"):
                st.markdown("#### Thread Bomber Output")
                st.write({"x_thread": (meta_by_module.get("thread_bomber") or {}).get("x_thread", [])})
            if meta_by_module.get("short_form_pack"):
                st.markdown("#### Short-form Pack Output")
                st.write({"short_form_pack": (meta_by_module.get("short_form_pack") or {}).get("short_form_pack", [])[:3]})

            st.markdown("#### Workflow Step Logs")
            st.dataframe([
                {
                    "step": s.get("step"),
                    "module": s.get("module"),
                    "status": s.get("status", "done"),
                    "message": (s.get("metadata") or {}).get("message")
                    or (s.get("metadata") or {}).get("error")
                    or ((s.get("metadata") or {}).get("v2_summary") or {}).get("error")
                    or "",
                }
                for s in steps
            ], use_container_width=True)
        else:
            st.json(data)

    st.divider()
    st.markdown("### 💎 Vault → Membership Pack")
    st.caption("Run `vault_to_membership_pack` to build a weekly member/newsletter bundle.")

    mem_topic = st.text_input("Membership topic", value="Sovereign Body Reset", key="mem_topic")
    mem_context = st.text_area("Membership context (optional)", value="", key="mem_context")
    memc1, memc2 = st.columns(2)
    mem_include_audio = memc1.checkbox("Include audio", value=False, key="mem_include_audio")
    mem_include_video = memc2.checkbox("Include video", value=False, key="mem_include_video")
    memc6, memc7, memc8 = st.columns(3)
    mem_generate_images = memc6.checkbox("Generate images", value=False, key="mem_generate_images")
    mem_image_style = memc7.selectbox("Image style", ["cinematic", "product", "social", "minimal", "cosmic"], index=0, key="mem_image_style")
    mem_num_images = memc8.number_input("# Images", min_value=1, max_value=8, value=3, step=1, key="mem_num_images")
    memc9, memc10, memc11 = st.columns(3)
    mem_generate_thumbs = memc9.checkbox("Generate thumbnails", value=False, key="mem_generate_thumbnails")
    mem_generate_covers = memc10.checkbox("Generate product covers", value=False, key="mem_generate_product_covers")
    mem_generate_social_visuals = memc11.checkbox("Generate social visuals", value=False, key="mem_generate_social_visuals")
    memc3, memc4, memc5 = st.columns(3)
    mem_gum_bonus = memc3.checkbox("Export Gumroad bonus", value=True, key="mem_export_gum_bonus")
    mem_yt_support = memc4.checkbox("Export YouTube supporting content", value=True, key="mem_export_yt_support")
    mem_payhip = memc5.checkbox("Export Payhip pack", value=True, key="mem_export_payhip")

    if st.button("Run vault_to_membership_pack", key="btn_run_membership_pack"):
        constraints = {
            "context": mem_context,
            "include_audio": bool(mem_include_audio),
            "include_video": bool(mem_include_video),
            "generate_images": bool(mem_generate_images),
            "image_style": mem_image_style,
            "num_images": int(mem_num_images),
            "generate_thumbnails": bool(mem_generate_thumbs),
            "generate_product_covers": bool(mem_generate_covers),
            "generate_social_visuals": bool(mem_generate_social_visuals),
            "export_newsletter_pack": True,
            "export_social_pack": True,
            "export_gumroad_bonus": bool(mem_gum_bonus),
            "export_youtube_supporting_content": bool(mem_yt_support),
            "export_payhip_pack": bool(mem_payhip),
        }
        with st.spinner("Running vault_to_membership_pack..."):
            r = requests.post(
                f"{base_url}/v1/workflows/vault_to_membership_pack/run",
                headers=headers(),
                json={"topic": mem_topic, "constraints": constraints, "dry_run": False},
                timeout=1800,
            )

        data = safe_json(r)
        status = str(data.get("status") or ("error" if r.status_code >= 400 else "done")).lower()
        if status == "done":
            st.success(f"Workflow status: {status}")
        elif status == "partial":
            st.warning(f"Workflow status: {status}")
        else:
            st.error(f"Workflow status: {status}")

        steps = data.get("steps") or []
        if isinstance(steps, list) and steps:
            meta_by_module = {s.get("module"): (s.get("metadata") or {}) for s in steps if isinstance(s, dict)}
            newsletter = meta_by_module.get("newsletter_packager") or {}
            social = meta_by_module.get("social_launch_packager") or {}
            product = meta_by_module.get("product_packager") or {}
            exporter = meta_by_module.get("content_exporter") or {}

            st.markdown("#### Newsletter Issue")
            st.write({
                "draft": newsletter.get("newsletter_issue_draft", ""),
                "free_teaser": newsletter.get("free_version_teaser", ""),
                "premium_section": newsletter.get("premium_version_section", ""),
                "upgrade_cta": newsletter.get("upgrade_cta", ""),
            })

            st.markdown("#### Premium / Bonus Asset Summary")
            st.write({
                "offer_name": product.get("product_name", ""),
                "bundle_contents": product.get("bundle_contents", []),
                "price_suggestion": product.get("price_suggestion", ""),
            })

            st.markdown("#### Social Launch")
            st.write(social)

            img_meta = meta_by_module.get("image_generator_v2") or {}
            if img_meta:
                st.markdown("#### Generated Images")
                st.write({"status": img_meta.get("status"), "prompts": img_meta.get("prompts_used", [])[:3]})
                for pth in (img_meta.get("image_paths") or [])[:6]:
                    if pth and os.path.exists(pth):
                        st.image(pth, caption=Path(pth).name, use_container_width=True)

            render_visual_outputs(meta_by_module)

            packs = (exporter.get("packs") or {})
            st.markdown("#### Optional Channel Support")
            st.write({
                "gumroad_bonus": packs.get("gumroad_bonus", ""),
                "youtube_supporting": packs.get("youtube_supporting", ""),
                "payhip": packs.get("payhip", ""),
            })

            st.markdown("#### Export Folder")
            st.write({"export_folder": exporter.get("export_folder", ""), "packs": packs, "preferred_final_assets": exporter.get("preferred_final_assets", {})})

            st.markdown("#### Step Status")
            st.dataframe([
                {
                    "step": s.get("step"),
                    "module": s.get("module"),
                    "status": s.get("status", "done"),
                    "message": (s.get("metadata") or {}).get("message")
                    or (s.get("metadata") or {}).get("error")
                    or ((s.get("metadata") or {}).get("v2_summary") or {}).get("error")
                    or "",
                }
                for s in steps
            ], use_container_width=True)
        else:
            st.json(data)


# --- Swarm ---
with tabs[14]:
    st.subheader("Swarm Mode (Director → Plan → Run → Audit)")
    st.caption("Swarm Mode picks a workflow automatically (heuristic or local Ollama) and executes it with full run logs.")

    sw_goal = st.text_area("Goal", value="Build a YouTube flywheel for a career sanctuary niche", key="sw_goal")
    sw_topic = st.text_input("Topic", value="Career Sanctuary", key="sw_topic")
    sw_constraints = st.text_area("Constraints JSON", value="{}", key="sw_constraints")
    sw_backend = st.selectbox("Director backend", ["heuristic", "ollama"], index=0, key="sw_backend")
    sw_session_id = st.number_input("Session ID (optional)", min_value=0, value=0, step=1, key="sw_session_id")
    sw_plan_id = st.number_input("Plan ID (optional)", min_value=0, value=0, step=1, key="sw_plan_id")

    colp1, colp2, colp3 = st.columns(3)
    if colp1.button("Plan", key="btn_sw_plan"):
        payload = {
            "goal": sw_goal,
            "topic": sw_topic,
            "constraints": json.loads(sw_constraints or "{}"),
            "prefer_backend": sw_backend,
            "session_id": int(sw_session_id) if int(sw_session_id) > 0 else None,
        }
        r = requests.post(f"{base_url}/v1/swarm/plan", headers=headers(), json=payload, timeout=120)
        st.json(safe_json(r))

    if colp2.button("Run", key="btn_sw_run"):
        payload = {
            "plan_id": int(sw_plan_id) if int(sw_plan_id) > 0 else None,
            "goal": sw_goal,
            "topic": sw_topic,
            "constraints": json.loads(sw_constraints or "{}"),
            "session_id": int(sw_session_id) if int(sw_session_id) > 0 else None,
            "dry_run": False,
        }
        r = requests.post(f"{base_url}/v1/swarm/run", headers=headers(), json=payload, timeout=1800)
        st.json(safe_json(r))

    if colp3.button("Audit", key="btn_sw_audit"):
        if int(sw_plan_id) <= 0:
            st.warning("Enter a run_id to audit in the Plan ID field (or paste run_id).")
        else:
            r = requests.post(f"{base_url}/v1/swarm/audit", headers=headers(), json={"run_id": int(sw_plan_id)}, timeout=120)
            st.json(safe_json(r))
