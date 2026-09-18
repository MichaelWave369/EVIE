from __future__ import annotations
import json, datetime, hashlib
from typing import Any, Dict, List, Optional
from app.db.schema import connect

def log_audit(actor: str, action: str, target_type: str | None, target_id: str | None, details: Dict[str, Any]) -> None:
    con = connect()
    con.execute(
        "INSERT INTO audit_log(ts, actor, action, target_type, target_id, details_json) VALUES (?,?,?,?,?,?)",
        (datetime.datetime.utcnow().isoformat(), actor, action, target_type, target_id, json.dumps(details, ensure_ascii=False))
    )
    con.commit()
    con.close()

def upsert_source(source_type: str, source_uri: str | None, title: str | None) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO sources(source_type, source_uri, title, created_at) VALUES (?,?,?,?)",
        (source_type, source_uri, title, now)
    )
    sid = int(cur.lastrowid)
    con.commit()
    con.close()
    return sid

def insert_document(source_id: int, raw_text: str, metadata: Dict[str, Any],
                    domain_id: int | None, phase_id: int | None, state_id: int | None, lens_id: int | None, canonical_key: str | None) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    h = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    cur = con.execute(
        "INSERT INTO documents(source_id, content_hash, raw_text, metadata_json, domain_id, phase_id, state_id, lens_id, canonical_key, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (source_id, h, raw_text, json.dumps(metadata, ensure_ascii=False), domain_id, phase_id, state_id, lens_id, canonical_key, now)
    )
    doc_id = int(cur.lastrowid)
    con.commit()
    con.close()
    return doc_id

def insert_chunks(doc_id: int, chunks: List[Dict[str, Any]]) -> List[int]:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    ids = []
    for c in chunks:
        cur = con.execute(
            "INSERT INTO chunks(doc_id, chunk_index, chunk_text, token_count, created_at) VALUES (?,?,?,?,?)",
            (doc_id, int(c["chunk_index"]), c["text"], int(c.get("token_count", 0)), now)
        )
        ids.append(int(cur.lastrowid))
    con.commit()
    con.close()
    return ids

def get_chunk_texts(chunk_ids: List[int]) -> List[str]:
    con = connect()
    q = "SELECT chunk_id, chunk_text FROM chunks WHERE chunk_id IN (%s)" % ",".join("?"*len(chunk_ids))
    rows = con.execute(q, chunk_ids).fetchall()
    con.close()
    by_id = {int(r["chunk_id"]): r["chunk_text"] for r in rows}
    return [by_id[i] for i in chunk_ids if i in by_id]

def get_doc(doc_id: int) -> Dict[str, Any]:
    con = connect()
    r = con.execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
    con.close()
    if not r:
        raise KeyError(f"doc_id {doc_id} not found")
    d = dict(r)
    d["metadata"] = json.loads(d["metadata_json"])
    return d


def get_chunks_with_docs(chunk_ids: List[int]) -> List[Dict[str, Any]]:
    if not chunk_ids:
        return []
    con = connect()
    q = """SELECT
        c.chunk_id, c.chunk_text, c.doc_id,
        d.canonical_key, d.domain_id, d.phase_id, d.state_id, d.lens_id, d.metadata_json
      FROM chunks c
      JOIN documents d ON d.doc_id = c.doc_id
      WHERE c.chunk_id IN (%s)
    """ % ",".join("?"*len(chunk_ids))
    rows = con.execute(q, chunk_ids).fetchall()
    con.close()
    by_id = {}
    for r in rows:
        d = dict(r)
        try:
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        by_id[int(d["chunk_id"])] = d
    # preserve input order
    return [by_id[i] for i in chunk_ids if i in by_id]

# -------- Products & Assets --------

def create_product(
    module: str,
    sku: str,
    name: str,
    description: str | None,
    price_cents: int,
    status: str,
    metadata: Dict[str, Any],
    product_key: str | None = None,
    current_version: str | None = None,
    campaign_id: int | None = None,
    session_id: int | None = None,
) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO products(module, sku, name, description, price_cents, status, metadata_json, created_at, product_key, current_version, updated_at, campaign_id, session_id)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            module,
            sku,
            name,
            description,
            int(price_cents),
            status,
            json.dumps(metadata, ensure_ascii=False),
            now,
            product_key,
            current_version,
            now,
            campaign_id,
            session_id,
        ),
    )
    pid = int(cur.lastrowid)
    con.commit()
    con.close()
    return pid


def attach_asset(product_id: int | None, asset_type: str, path: str) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO assets(product_id, asset_type, path, created_at) VALUES (?,?,?,?)",
        (product_id, asset_type, path, now)
    )
    aid = int(cur.lastrowid)
    con.commit()
    con.close()
    return aid

def list_products(limit: int = 100) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute("SELECT * FROM products ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
    con.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        out.append(d)
    return out

def get_product(product_id: int) -> Dict[str, Any]:
    con = connect()
    r = con.execute("SELECT * FROM products WHERE product_id=?", (int(product_id),)).fetchone()
    con.close()
    if not r:
        raise KeyError(f"product_id {product_id} not found")
    d = dict(r)
    try:
        d["metadata"] = json.loads(d.get("metadata_json") or "{}")
    except Exception:
        d["metadata"] = {}
    return d

def list_assets(product_id: int) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute("SELECT * FROM assets WHERE product_id=? ORDER BY created_at ASC", (int(product_id),)).fetchall()
    con.close()
    return [dict(r) for r in rows]

# ---- Product Versioning ----

def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    con = connect()
    row = con.execute("SELECT * FROM products WHERE sku=?", (sku,)).fetchone()
    con.close()
    return dict(row) if row else None

def update_product(product_id: int, *, name: str | None = None, description: str | None = None, price_cents: int | None = None,
                   status: str | None = None, metadata: Dict[str, Any] | None = None, current_version: str | None = None) -> None:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    fields = []
    vals = []
    if name is not None:
        fields.append("name=?"); vals.append(name)
    if description is not None:
        fields.append("description=?"); vals.append(description)
    if price_cents is not None:
        fields.append("price_cents=?"); vals.append(int(price_cents))
    if status is not None:
        fields.append("status=?"); vals.append(status)
    if metadata is not None:
        fields.append("metadata_json=?"); vals.append(json.dumps(metadata, ensure_ascii=False))
    if current_version is not None:
        fields.append("current_version=?"); vals.append(current_version)
    fields.append("updated_at=?"); vals.append(now)
    vals.append(int(product_id))
    con.execute(f"UPDATE products SET {', '.join(fields)} WHERE product_id=?", tuple(vals))
    con.commit()
    con.close()

def create_product_version(product_id: int, version: str, bundle_zip: str, changelog: str, metadata: Dict[str, Any]) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO product_versions(product_id, version, bundle_zip, changelog, metadata_json, created_at) VALUES (?,?,?,?,?,?)",
        (int(product_id), version, bundle_zip, changelog, json.dumps(metadata, ensure_ascii=False), now),
    )
    vid = int(cur.lastrowid)
    con.commit()
    con.close()
    return vid

def list_product_versions(product_id: int) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute(
        "SELECT * FROM product_versions WHERE product_id=? ORDER BY created_at DESC",
        (int(product_id),),
    ).fetchall()
    con.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        out.append(d)
    return out

def get_latest_version(product_id: int) -> Optional[str]:
    con = connect()
    row = con.execute("SELECT version FROM product_versions WHERE product_id=? ORDER BY created_at DESC LIMIT 1", (int(product_id),)).fetchone()
    con.close()
    return row[0] if row else None

# ---- Metrics runs ----

def create_metrics_run(source: str | None, filename: str | None, path: str, summary: Dict[str, Any] | None = None) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO metrics_runs(source, filename, path, summary_json, created_at) VALUES (?,?,?,?,?)",
        (source, filename, path, json.dumps(summary or {}, ensure_ascii=False), now),
    )
    rid = int(cur.lastrowid)
    con.commit()
    con.close()
    return rid

def update_metrics_run(run_id: int, summary: Dict[str, Any]) -> None:
    con = connect()
    con.execute("UPDATE metrics_runs SET summary_json=? WHERE run_id=?", (json.dumps(summary, ensure_ascii=False), int(run_id)))
    con.commit()
    con.close()

def list_metrics_runs(limit: int = 25) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute("SELECT * FROM metrics_runs ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
    con.close()
    out=[]
    for r in rows:
        d=dict(r)
        try:
            d["summary"] = json.loads(d.get("summary_json") or "{}")
        except Exception:
            d["summary"] = {}
        out.append(d)
    return out


# ---- Tasks (Scheduler) ----

def list_tasks(status: str | None = None, limit: int = 50) -> List[Dict[str, Any]]:
    con = connect()
    if status:
        rows = con.execute("SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, int(limit))).fetchall()
    else:
        rows = con.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
    con.close()
    out=[]
    for r in rows:
        d=dict(r)
        try:
            d["payload"] = json.loads(d.get("payload_json") or "{}")
        except Exception:
            d["payload"] = {}
        try:
            d["last_result"] = json.loads(d.get("last_result_json") or "{}")
        except Exception:
            d["last_result"] = {}
        out.append(d)
    return out

def fetch_due_tasks(now_iso: str, limit: int = 10) -> List[Dict[str, Any]]:
    # schedule_at is ISO; NULL means run ASAP
    con = connect()
    rows = con.execute(
        "SELECT * FROM tasks WHERE status='queued' AND (schedule_at IS NULL OR schedule_at <= ?) ORDER BY COALESCE(schedule_at, created_at) ASC LIMIT ?",
        (now_iso, int(limit)),
    ).fetchall()
    con.close()
    out=[]
    for r in rows:
        d=dict(r)
        try:
            d["payload"] = json.loads(d.get("payload_json") or "{}")
        except Exception:
            d["payload"] = {}
        out.append(d)
    return out

def set_task_status(task_id: int, status: str, *, last_result: Dict[str, Any] | None = None) -> None:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    con.execute(
        "UPDATE tasks SET status=?, last_run_at=?, last_result_json=? WHERE task_id=?",
        (status, now, json.dumps(last_result or {}, ensure_ascii=False), int(task_id)),
    )
    con.commit()
    con.close()


# ---- Product Factory Queue ----

def enqueue_queue_item(topic: str, modules: List[str], constraints: Dict[str, Any], priority: int = 0) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO product_queue(topic, status, priority, modules_json, constraints_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (topic, "queued", int(priority), json.dumps(modules, ensure_ascii=False), json.dumps(constraints or {}, ensure_ascii=False), now, now),
    )
    qid = int(cur.lastrowid)
    con.commit()
    con.close()
    return qid

def list_queue(status: str | None = None, limit: int = 100) -> List[Dict[str, Any]]:
    con = connect()
    if status:
        rows = con.execute("SELECT * FROM product_queue WHERE status=? ORDER BY priority DESC, created_at ASC LIMIT ?", (status, int(limit))).fetchall()
    else:
        rows = con.execute("SELECT * FROM product_queue ORDER BY status ASC, priority DESC, created_at ASC LIMIT ?", (int(limit),)).fetchall()
    con.close()
    out=[]
    for r in rows:
        d=dict(r)
        try:
            d["modules"] = json.loads(d.get("modules_json") or "[]")
        except Exception:
            d["modules"] = []
        try:
            d["constraints"] = json.loads(d.get("constraints_json") or "{}")
        except Exception:
            d["constraints"] = {}
        try:
            d["result"] = json.loads(d.get("result_json") or "{}")
        except Exception:
            d["result"] = {}
        out.append(d)
    return out

def claim_next_queue_item() -> Optional[Dict[str, Any]]:
    con = connect()
    row = con.execute(
        "SELECT * FROM product_queue WHERE status='queued' ORDER BY priority DESC, created_at ASC LIMIT 1"
    ).fetchone()
    if not row:
        con.close()
        return None
    qid = int(row["queue_id"])
    now = datetime.datetime.utcnow().isoformat()
    con.execute("UPDATE product_queue SET status='running', updated_at=? WHERE queue_id=?", (now, qid))
    con.commit()
    con.close()
    d = dict(row)
    d["queue_id"] = qid
    try:
        d["modules"] = json.loads(d.get("modules_json") or "[]")
    except Exception:
        d["modules"] = []
    try:
        d["constraints"] = json.loads(d.get("constraints_json") or "{}")
    except Exception:
        d["constraints"] = {}
    return d

def finish_queue_item(queue_id: int, status: str, result: Dict[str, Any] | None = None, err: str | None = None) -> None:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    con.execute(
        "UPDATE product_queue SET status=?, result_json=?, last_error=?, updated_at=? WHERE queue_id=?",
        (status, json.dumps(result or {}, ensure_ascii=False), err, now, int(queue_id)),
    )
    con.commit()
    con.close()


# ---- Schedule Rules ----

def create_schedule_rule(name: str, cadence: str = "fib_369_weekly", hour_utc: int = 15, sku_prefix: str | None = None, metadata: Dict[str, Any] | None = None) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO schedule_rules(name, sku_prefix, cadence, hour_utc, enabled, metadata_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (name, sku_prefix, cadence, int(hour_utc), 1, json.dumps(metadata or {}, ensure_ascii=False), now, now),
    )
    rid = int(cur.lastrowid)
    con.commit()
    con.close()
    return rid

def list_schedule_rules(limit: int = 50) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute("SELECT * FROM schedule_rules ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
    con.close()
    out=[]
    for r in rows:
        d=dict(r)
        try:
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        out.append(d)
    return out


# ---- Artifact Fingerprints (Integrity / Anti-duplicate guard) ----

def add_fingerprint(sku: str, version: str, path: str, sha256: str, size_bytes: int) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO artifact_fingerprints(sku, version, path, sha256, size_bytes, created_at) VALUES (?,?,?,?,?,?)",
        (sku, version, path, sha256, int(size_bytes), now),
    )
    fid = int(cur.lastrowid)
    con.commit()
    con.close()
    return fid

def find_by_sha(sha256: str, limit: int = 50) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute("SELECT * FROM artifact_fingerprints WHERE sha256=? ORDER BY created_at DESC LIMIT ?", (sha256, int(limit))).fetchall()
    con.close()
    return [dict(r) for r in rows]

def list_fingerprints_for_sku(sku: str, limit: int = 500) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute("SELECT * FROM artifact_fingerprints WHERE sku=? ORDER BY created_at DESC LIMIT ?", (sku, int(limit))).fetchall()
    con.close()
    return [dict(r) for r in rows]


# ---- Run history (observability / reproducibility) ----

def create_run(run_type: str, module: str | None, topic: str | None, input_obj: Dict[str, Any], actor: str = "system", campaign_id: int | None = None, session_id: int | None = None) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO runs(run_type, module, topic, status, input_json, started_at, created_at, campaign_id, session_id) VALUES (?,?,?,?,?,?,?,?,?)",
        (run_type, module, topic, "running", json.dumps(input_obj or {}, ensure_ascii=False), now, now, campaign_id, session_id),
    )
    rid = int(cur.lastrowid)
    con.commit()
    con.close()
    log_audit(actor, "run_start", "run", str(rid), {"run_type": run_type, "module": module, "topic": topic})
    return rid

def finish_run(run_id: int, status: str, output_obj: Dict[str, Any] | None = None, error: str | None = None) -> None:
    con = connect()
    end = datetime.datetime.utcnow().isoformat()
    row = con.execute("SELECT started_at FROM runs WHERE run_id=?", (int(run_id),)).fetchone()
    started = None
    if row:
        started = row["started_at"]
    dur = None
    try:
        if started:
            t0 = datetime.datetime.fromisoformat(started)
            t1 = datetime.datetime.fromisoformat(end)
            dur = int((t1 - t0).total_seconds() * 1000)
    except Exception:
        dur = None

    con.execute(
        "UPDATE runs SET status=?, output_json=?, error=?, ended_at=?, duration_ms=? WHERE run_id=?",
        (status, json.dumps(output_obj or {}, ensure_ascii=False), error, end, dur, int(run_id)),
    )
    con.commit()
    con.close()

def create_run_step(run_id: int, step_index: int, step_type: str, module: str | None, input_obj: Dict[str, Any]) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO run_steps(run_id, step_index, step_type, module, status, input_json, started_at) VALUES (?,?,?,?,?,?,?)",
        (int(run_id), int(step_index), step_type, module, "running", json.dumps(input_obj or {}, ensure_ascii=False), now),
    )
    sid = int(cur.lastrowid)
    con.commit()
    con.close()
    return sid

def finish_run_step(step_id: int, status: str, output_obj: Dict[str, Any] | None = None, error: str | None = None) -> None:
    con = connect()
    end = datetime.datetime.utcnow().isoformat()
    row = con.execute("SELECT started_at FROM run_steps WHERE step_id=?", (int(step_id),)).fetchone()
    started = None
    if row:
        started = row["started_at"]
    dur = None
    try:
        if started:
            t0 = datetime.datetime.fromisoformat(started)
            t1 = datetime.datetime.fromisoformat(end)
            dur = int((t1 - t0).total_seconds() * 1000)
    except Exception:
        dur = None

    con.execute(
        "UPDATE run_steps SET status=?, output_json=?, error=?, ended_at=?, duration_ms=? WHERE step_id=?",
        (status, json.dumps(output_obj or {}, ensure_ascii=False), error, end, dur, int(step_id)),
    )
    con.commit()
    con.close()

def list_runs(limit: int = 50, status: str | None = None) -> List[Dict[str, Any]]:
    con = connect()
    if status:
        rows = con.execute("SELECT * FROM runs WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, int(limit))).fetchall()
    else:
        rows = con.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
    con.close()
    out=[]
    for r in rows:
        d=dict(r)
        try:
            d["input"] = json.loads(d.get("input_json") or "{}")
        except Exception:
            d["input"] = {}
        try:
            d["output"] = json.loads(d.get("output_json") or "{}")
        except Exception:
            d["output"] = {}
        out.append(d)
    return out

def get_run(run_id: int) -> Dict[str, Any]:
    con = connect()
    r = con.execute("SELECT * FROM runs WHERE run_id=?", (int(run_id),)).fetchone()
    if not r:
        con.close()
        raise KeyError(f"run_id {run_id} not found")
    d=dict(r)
    steps = con.execute("SELECT * FROM run_steps WHERE run_id=? ORDER BY step_index ASC, step_id ASC", (int(run_id),)).fetchall()
    con.close()
    try:
        d["input"] = json.loads(d.get("input_json") or "{}")
    except Exception:
        d["input"] = {}
    try:
        d["output"] = json.loads(d.get("output_json") or "{}")
    except Exception:
        d["output"] = {}
    d_steps=[]
    for s in steps:
        sd=dict(s)
        try:
            sd["input"] = json.loads(sd.get("input_json") or "{}")
        except Exception:
            sd["input"] = {}
        try:
            sd["output"] = json.loads(sd.get("output_json") or "{}")
        except Exception:
            sd["output"] = {}
        d_steps.append(sd)
    d["steps"] = d_steps
    return d



# ---- Campaigns / Sessions / Evidence ----

def create_campaign(
    name: str,
    niche: str | None = None,
    audience: str | None = None,
    promise: str | None = None,
    platforms: Dict[str, Any] | None = None,
    status: str = "active",
    metadata: Dict[str, Any] | None = None,
    campaign_key: str | None = None,
) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        """INSERT INTO campaigns(campaign_key, name, niche, audience, promise, platforms_json, status, metadata_json, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            campaign_key,
            name,
            niche,
            audience,
            promise,
            json.dumps(platforms or {}, ensure_ascii=False),
            status,
            json.dumps(metadata or {}, ensure_ascii=False),
            now,
            now,
        ),
    )
    cid = int(cur.lastrowid)
    con.commit()
    con.close()
    try:
        from app.search.fts import upsert as _fts_upsert
        _fts_upsert(ref_type="campaign", ref_id=str(cid), campaign_id=cid, title=name, body="\n".join([niche or "", audience or "", promise or ""]))
    except Exception:
        pass
    return cid

def list_campaigns(limit: int = 100) -> List[Dict[str, Any]]:
    con = connect()
    rows = con.execute("SELECT * FROM campaigns ORDER BY updated_at DESC LIMIT ?", (int(limit),)).fetchall()
    con.close()
    out=[]
    for r in rows:
        d=dict(r)
        try:
            d["platforms"] = json.loads(d.get("platforms_json") or "{}")
        except Exception:
            d["platforms"] = {}
        try:
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        out.append(d)
    return out

def get_campaign(campaign_id: int) -> Dict[str, Any]:
    con = connect()
    r = con.execute("SELECT * FROM campaigns WHERE campaign_id=?", (int(campaign_id),)).fetchone()
    con.close()
    if not r:
        raise KeyError(f"campaign_id {campaign_id} not found")
    d=dict(r)
    try:
        d["platforms"] = json.loads(d.get("platforms_json") or "{}")
    except Exception:
        d["platforms"] = {}
    try:
        d["metadata"] = json.loads(d.get("metadata_json") or "{}")
    except Exception:
        d["metadata"] = {}
    return d

def create_session(campaign_id: int | None, name: str, notes: str | None = None, status: str = "open") -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO sessions(campaign_id, name, status, notes, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        (int(campaign_id) if campaign_id is not None else None, name, status, notes, now, now),
    )
    sid = int(cur.lastrowid)
    con.commit()
    con.close()
    try:
        from app.search.fts import upsert as _fts_upsert
        _fts_upsert(ref_type="session", ref_id=str(sid), campaign_id=campaign_id, session_id=sid, title=name, body=notes or "")
    except Exception:
        pass
    return sid

def list_sessions(campaign_id: int | None = None, limit: int = 200) -> List[Dict[str, Any]]:
    con = connect()
    if campaign_id is None:
        rows = con.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (int(limit),)).fetchall()
    else:
        rows = con.execute("SELECT * FROM sessions WHERE campaign_id=? ORDER BY updated_at DESC LIMIT ?", (int(campaign_id), int(limit))).fetchall()
    con.close()
    return [dict(r) for r in rows]

def create_evidence(
    campaign_id: int | None,
    kind: str,
    title: str,
    url: str | None = None,
    content: str | None = None,
    file_path: str | None = None,
    sensitive: bool = False,
    tags: List[str] | None = None,
    product_id: int | None = None,
    session_id: int | None = None,
) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        """INSERT INTO evidence_items(campaign_id, product_id, session_id, kind, title, url, content, file_path, sensitive, tags_json, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            int(campaign_id) if campaign_id is not None else None,
            int(product_id) if product_id is not None else None,
            int(session_id) if session_id is not None else None,
            kind,
            title,
            url,
            content,
            file_path,
            1 if sensitive else 0,
            json.dumps(tags or [], ensure_ascii=False),
            now,
        ),
    )
    eid = int(cur.lastrowid)
    con.commit()
    con.close()
    try:
        from app.search.fts import upsert as _fts_upsert
        _fts_upsert(ref_type="evidence", ref_id=str(eid), campaign_id=campaign_id, session_id=session_id, title=title, body="\n".join([url or "", content or "", file_path or "", " ".join(tags or [])]))
    except Exception:
        pass
    return eid

def list_evidence(campaign_id: int | None = None, product_id: int | None = None, limit: int = 200) -> List[Dict[str, Any]]:
    con = connect()
    if product_id is not None:
        rows = con.execute(
            "SELECT * FROM evidence_items WHERE product_id=? ORDER BY created_at DESC LIMIT ?",
            (int(product_id), int(limit)),
        ).fetchall()
    elif campaign_id is not None:
        rows = con.execute(
            "SELECT * FROM evidence_items WHERE campaign_id=? ORDER BY created_at DESC LIMIT ?",
            (int(campaign_id), int(limit)),
        ).fetchall()
    else:
        rows = con.execute("SELECT * FROM evidence_items ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
    con.close()
    out=[]
    for r in rows:
        d=dict(r)
        try:
            d["tags"] = json.loads(d.get("tags_json") or "[]")
        except Exception:
            d["tags"] = []
        out.append(d)
    return out
