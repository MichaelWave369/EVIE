from __future__ import annotations
import sqlite3
from pathlib import Path
from app.settings import settings

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS taxonomy_domain (
  domain_id INTEGER PRIMARY KEY,
  domain_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taxonomy_phase (
  phase_id INTEGER PRIMARY KEY,
  phase_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taxonomy_state (
  state_id INTEGER PRIMARY KEY,
  state_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taxonomy_lens (
  lens_id INTEGER PRIMARY KEY,
  lens_code TEXT NOT NULL,
  lens_name TEXT NOT NULL,
  lens_description TEXT,
  safety_tier INTEGER NOT NULL DEFAULT 0,
  gate_profile TEXT,
  operator_default TEXT,
  allowed_outputs TEXT
);

CREATE TABLE IF NOT EXISTS cell20736 (
  cell20736_id INTEGER PRIMARY KEY,
  cell1728_id INTEGER,
  domain_id INTEGER NOT NULL,
  phase_id INTEGER NOT NULL,
  state_id INTEGER NOT NULL,
  lens_id INTEGER NOT NULL,
  canonical_key TEXT NOT NULL,
  safety_tier INTEGER NOT NULL DEFAULT 0,
  gate_profile TEXT,
  operator_default TEXT,
  allowed_outputs TEXT,
  UNIQUE(domain_id, phase_id, state_id, lens_id),
  FOREIGN KEY(domain_id) REFERENCES taxonomy_domain(domain_id),
  FOREIGN KEY(phase_id) REFERENCES taxonomy_phase(phase_id),
  FOREIGN KEY(state_id) REFERENCES taxonomy_state(state_id),
  FOREIGN KEY(lens_id) REFERENCES taxonomy_lens(lens_id)
);

CREATE TABLE IF NOT EXISTS sources (
  source_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL,         -- file | text | url
  source_uri TEXT,                   -- local path or identifier
  title TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
  doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id INTEGER,
  content_hash TEXT NOT NULL,
  raw_text TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  domain_id INTEGER,
  phase_id INTEGER,
  state_id INTEGER,
  lens_id INTEGER,
  canonical_key TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS chunks (
  chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id INTEGER NOT NULL,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  token_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
);

CREATE TABLE IF NOT EXISTS vector_meta (
  vector_id INTEGER PRIMARY KEY AUTOINCREMENT,
  chunk_id INTEGER NOT NULL UNIQUE,
  model TEXT NOT NULL,
  dims INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(chunk_id) REFERENCES chunks(chunk_id)
);

CREATE TABLE IF NOT EXISTS products (
  product_id INTEGER PRIMARY KEY AUTOINCREMENT,
  module TEXT NOT NULL,      -- ebooks | youtube | etsy | newsletter | ...
  sku TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT,
  price_cents INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'draft',
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
  asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER,
  asset_type TEXT NOT NULL, -- pdf | md | zip | json | txt
  path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id INTEGER PRIMARY KEY AUTOINCREMENT,
  module TEXT NOT NULL,
  task_type TEXT NOT NULL,  -- ingest | generate | export | analytics
  payload_json TEXT NOT NULL,
  schedule_at TEXT,
  status TEXT NOT NULL DEFAULT 'queued',
  last_run_at TEXT,
  last_result_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  details_json TEXT NOT NULL
);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_all USING fts5(
  ref_type UNINDEXED,
  ref_id UNINDEXED,
  campaign_id UNINDEXED,
  session_id UNINDEXED,
  sku UNINDEXED,
  title,
  body,
  tokenize = 'porter'
);
"""

import threading as _threading

_local = _threading.local()
_dirs_created = False


def connect() -> sqlite3.Connection:
    """Return a thread-local cached SQLite connection.

    Eliminates the overhead of opening/closing a connection on every DB call
    (which was ~100+ open/close cycles per flywheel build).
    """
    global _dirs_created
    if not _dirs_created:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.vault_files_dir.mkdir(parents=True, exist_ok=True)
        settings.index_dir.mkdir(parents=True, exist_ok=True)
        _dirs_created = True

    con = getattr(_local, "conn", None)
    if con is not None:
        try:
            con.execute("SELECT 1")
            return con
        except Exception:
            # Connection is stale/broken; recreate
            try:
                con.close()
            except Exception:
                pass
            _local.conn = None

    con = sqlite3.connect(str(settings.db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    _local.conn = con
    return con


def _has_column(con: sqlite3.Connection, table: str, col: str) -> bool:
    cur = con.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def _add_column(con: sqlite3.Connection, table: str, col_def: str) -> None:
    con.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")

def init_db() -> None:
    con = connect()
    try:
        con.executescript(SCHEMA_SQL)

        # ---- Lightweight migrations (safe, local-only) ----
        # products: add product_key + version tracking
        if not _has_column(con, "products", "product_key"):
            _add_column(con, "products", "product_key TEXT")
        if not _has_column(con, "products", "current_version"):
            _add_column(con, "products", "current_version TEXT")
        if not _has_column(con, "products", "updated_at"):
            _add_column(con, "products", "updated_at TEXT")

        # product_versions: versioned bundles + changelog
        con.executescript("""
        CREATE TABLE IF NOT EXISTS product_versions (
          version_id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_id INTEGER NOT NULL,
          version TEXT NOT NULL,
          bundle_zip TEXT NOT NULL,
          changelog TEXT,
          metadata_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(product_id) REFERENCES products(product_id)
        );
        CREATE INDEX IF NOT EXISTS idx_product_versions_product ON product_versions(product_id);
        """)

        # metrics_runs: store imported metrics analysis (CSV stays on disk)
        con.executescript("""
        CREATE TABLE IF NOT EXISTS metrics_runs (
          run_id INTEGER PRIMARY KEY AUTOINCREMENT,
          source TEXT,
          filename TEXT,
          path TEXT NOT NULL,
          summary_json TEXT,
          created_at TEXT NOT NULL
        );
        """)



        # ---- Run history (observability / reproducibility) ----
        con.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
          run_id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_type TEXT NOT NULL,                 -- module | offer | factory
          module TEXT,                            -- module name when run_type=module
          topic TEXT,
          status TEXT NOT NULL DEFAULT 'running', -- running | done | error
          input_json TEXT NOT NULL,
          output_json TEXT,
          error TEXT,
          started_at TEXT NOT NULL,
          ended_at TEXT,
          duration_ms INTEGER,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_runs_status_created ON runs(status, created_at);

        CREATE TABLE IF NOT EXISTS run_steps (
          step_id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id INTEGER NOT NULL,
          step_index INTEGER NOT NULL DEFAULT 0,
          step_type TEXT NOT NULL,                -- module | stamping | package | integrity
          module TEXT,
          status TEXT NOT NULL DEFAULT 'running',
          input_json TEXT NOT NULL,
          output_json TEXT,
          error TEXT,
          started_at TEXT NOT NULL,
          ended_at TEXT,
          duration_ms INTEGER,
          FOREIGN KEY(run_id) REFERENCES runs(run_id)
        );
        CREATE INDEX IF NOT EXISTS idx_run_steps_run ON run_steps(run_id, step_index);
        """)

        # tasks: link scheduler tasks to a run_id (optional)
        if not _has_column(con, "tasks", "run_id"):
            _add_column(con, "tasks", "run_id INTEGER")

        # ---- Product Factory + Scheduler + Integrity ----
        con.executescript("""
        CREATE TABLE IF NOT EXISTS product_queue (
  queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',   -- queued | running | done | error | skipped
  priority INTEGER NOT NULL DEFAULT 0,
  modules_json TEXT NOT NULL,
  constraints_json TEXT NOT NULL,
  last_error TEXT,
  result_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_product_queue_status_priority ON product_queue(status, priority, created_at);

CREATE TABLE IF NOT EXISTS schedule_rules (
  rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  sku_prefix TEXT,
  cadence TEXT NOT NULL DEFAULT 'fib_369_weekly', -- fib_369_weekly | fib_once | daily | weekly
  hour_utc INTEGER NOT NULL DEFAULT 15,
  enabled INTEGER NOT NULL DEFAULT 1,
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifact_fingerprints (
  fp_id INTEGER PRIMARY KEY AUTOINCREMENT,
  sku TEXT NOT NULL,
  version TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fp_sha ON artifact_fingerprints(sha256);
CREATE INDEX IF NOT EXISTS idx_fp_sku ON artifact_fingerprints(sku);
        """)

        # ---- Campaigns / Sessions / Evidence (Reconnect + Swarm ops layer) ----
        con.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
  campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_key TEXT UNIQUE,
  name TEXT NOT NULL,
  niche TEXT,
  audience TEXT,
  promise TEXT,
  platforms_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status, updated_at);

CREATE TABLE IF NOT EXISTS sessions (
  session_id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id INTEGER,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(campaign_id) REFERENCES campaigns(campaign_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_campaign ON sessions(campaign_id, updated_at);

CREATE TABLE IF NOT EXISTS evidence_items (
  evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id INTEGER,
  product_id INTEGER,
  session_id INTEGER,
  kind TEXT NOT NULL,              -- link | note | file
  title TEXT NOT NULL,
  url TEXT,
  content TEXT,
  file_path TEXT,
  sensitive INTEGER NOT NULL DEFAULT 0,
  tags_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
  FOREIGN KEY(product_id) REFERENCES products(product_id) ON DELETE SET NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_campaign ON evidence_items(campaign_id, created_at);
CREATE INDEX IF NOT EXISTS idx_evidence_product ON evidence_items(product_id, created_at);
        """)

        # Link runs/products/tasks to campaign/session (optional)
        for tbl in ["products", "runs", "tasks"]:
            if not _has_column(con, tbl, "campaign_id"):
                _add_column(con, tbl, "campaign_id INTEGER")
            if not _has_column(con, tbl, "session_id"):
                _add_column(con, tbl, "session_id INTEGER")

        # Optional full-text search index (FTS5). If the SQLite build lacks FTS5, EVIE falls back to LIKE.
        try:
            con.executescript(FTS_SQL)
        except Exception:
            pass

        con.commit()
    finally:
        try:
            con.close()
        except Exception:
            pass
