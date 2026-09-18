from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from app.db.schema import connect
from app.settings import settings


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def fts_available() -> bool:
    if not getattr(settings, "fts_enabled", True):
        return False
    con = connect()
    ok = _table_exists(con, "fts_all")
    con.close()
    return bool(ok)


def ensure_fts() -> bool:
    """Best-effort creation of fts_all.

    EVIE will work without FTS5 (it will fall back to LIKE search).
    """
    if not getattr(settings, "fts_enabled", True):
        return False
    con = connect()
    try:
        if _table_exists(con, "fts_all"):
            return True
        # Create FTS table; may fail if SQLite lacks FTS5.
        con.executescript(
            """
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
        )
        con.commit()
        return True
    except Exception:
        return False
    finally:
        con.close()


def upsert(
    *,
    ref_type: str,
    ref_id: str,
    title: str,
    body: str,
    campaign_id: Optional[int] = None,
    session_id: Optional[int] = None,
    sku: Optional[str] = None,
) -> None:
    if not ensure_fts():
        return
    con = connect()
    try:
        con.execute(
            "DELETE FROM fts_all WHERE ref_type=? AND ref_id=?",
            (ref_type, str(ref_id)),
        )
        con.execute(
            "INSERT INTO fts_all(ref_type, ref_id, campaign_id, session_id, sku, title, body) VALUES (?,?,?,?,?,?,?)",
            (
                ref_type,
                str(ref_id),
                int(campaign_id) if campaign_id is not None else None,
                int(session_id) if session_id is not None else None,
                sku,
                title or "",
                body or "",
            ),
        )
        con.commit()
    finally:
        con.close()


def delete(*, ref_type: str, ref_id: str) -> None:
    if not ensure_fts():
        return
    con = connect()
    try:
        con.execute(
            "DELETE FROM fts_all WHERE ref_type=? AND ref_id=?",
            (ref_type, str(ref_id)),
        )
        con.commit()
    finally:
        con.close()


def search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Return FTS hits. Falls back to LIKE if FTS is unavailable."""
    q = (query or "").strip()
    if not q:
        return []

    con = connect()
    try:
        if ensure_fts():
            rows = con.execute(
                """
                SELECT ref_type, ref_id, campaign_id, session_id, sku, title,
                       snippet(fts_all, 6, '<b>', '</b>', '…', 10) AS snippet,
                       bm25(fts_all) AS score
                  FROM fts_all
                 WHERE fts_all MATCH ?
                 ORDER BY score
                 LIMIT ?
                """,
                (q, int(limit)),
            ).fetchall()
            return [dict(r) for r in rows]

        # Fallback: slow LIKE across products + evidence + documents.
        like = f"%{q}%"
        out: List[Dict[str, Any]] = []
        # products
        for r in con.execute(
            "SELECT product_id AS ref_id, 'product' AS ref_type, campaign_id, session_id, sku, name AS title, description AS snippet FROM products WHERE name LIKE ? OR description LIKE ? LIMIT ?",
            (like, like, int(limit)),
        ).fetchall():
            out.append(dict(r))
        # evidence
        for r in con.execute(
            "SELECT evidence_id AS ref_id, 'evidence' AS ref_type, campaign_id, session_id, NULL AS sku, title, substr(coalesce(content,''),1,200) AS snippet FROM evidence_items WHERE title LIKE ? OR content LIKE ? LIMIT ?",
            (like, like, int(limit)),
        ).fetchall():
            out.append(dict(r))
        # documents
        for r in con.execute(
            "SELECT doc_id AS ref_id, 'doc' AS ref_type, NULL AS campaign_id, NULL AS session_id, NULL AS sku, coalesce(json_extract(metadata_json,'$.title'),'Document') AS title, substr(raw_text,1,200) AS snippet FROM documents WHERE raw_text LIKE ? LIMIT ?",
            (like, int(limit)),
        ).fetchall():
            out.append(dict(r))
        return out[: int(limit)]
    finally:
        con.close()


def rebuild(limit_docs: int = 200) -> Dict[str, Any]:
    """Best-effort rebuild of FTS index from key tables."""
    if not ensure_fts():
        return {"ok": False, "fts": False, "reason": "fts5 unavailable"}

    con = connect()
    try:
        con.execute("DELETE FROM fts_all")

        # campaigns
        for r in con.execute(
            "SELECT campaign_id, name, niche, audience, promise, platforms_json, metadata_json FROM campaigns"
        ).fetchall():
            body = "\n".join(
                [
                    r["niche"] or "",
                    r["audience"] or "",
                    r["promise"] or "",
                    r["platforms_json"] or "",
                    r["metadata_json"] or "",
                ]
            )
            con.execute(
                "INSERT INTO fts_all(ref_type, ref_id, campaign_id, session_id, sku, title, body) VALUES (?,?,?,?,?,?,?)",
                ("campaign", str(r["campaign_id"]), int(r["campaign_id"]), None, None, r["name"], body),
            )

        # sessions
        for r in con.execute(
            "SELECT session_id, campaign_id, name, status, notes FROM sessions"
        ).fetchall():
            body = "\n".join([r["status"] or "", r["notes"] or ""])  # type: ignore
            con.execute(
                "INSERT INTO fts_all(ref_type, ref_id, campaign_id, session_id, sku, title, body) VALUES (?,?,?,?,?,?,?)",
                (
                    "session",
                    str(r["session_id"]),
                    int(r["campaign_id"]) if r["campaign_id"] is not None else None,
                    int(r["session_id"]),
                    None,
                    r["name"],
                    body,
                ),
            )

        # products
        for r in con.execute(
            "SELECT product_id, campaign_id, session_id, sku, name, description, metadata_json FROM products"
        ).fetchall():
            body = "\n".join([r["description"] or "", r["metadata_json"] or ""])  # type: ignore
            con.execute(
                "INSERT INTO fts_all(ref_type, ref_id, campaign_id, session_id, sku, title, body) VALUES (?,?,?,?,?,?,?)",
                (
                    "product",
                    str(r["product_id"]),
                    int(r["campaign_id"]) if r["campaign_id"] is not None else None,
                    int(r["session_id"]) if r["session_id"] is not None else None,
                    r["sku"],
                    r["name"],
                    body,
                ),
            )

        # evidence
        for r in con.execute(
            "SELECT evidence_id, campaign_id, product_id, session_id, kind, title, url, content, file_path, tags_json FROM evidence_items"
        ).fetchall():
            body = "\n".join(
                [
                    r["kind"] or "",
                    r["url"] or "",
                    r["content"] or "",
                    r["file_path"] or "",
                    r["tags_json"] or "",
                ]
            )
            con.execute(
                "INSERT INTO fts_all(ref_type, ref_id, campaign_id, session_id, sku, title, body) VALUES (?,?,?,?,?,?,?)",
                (
                    "evidence",
                    str(r["evidence_id"]),
                    int(r["campaign_id"]) if r["campaign_id"] is not None else None,
                    int(r["session_id"]) if r["session_id"] is not None else None,
                    None,
                    r["title"],
                    body,
                ),
            )

        # documents (cap to avoid giant index)
        rows = con.execute(
            "SELECT doc_id, metadata_json, substr(raw_text,1,4000) AS body FROM documents ORDER BY created_at DESC LIMIT ?",
            (int(limit_docs),),
        ).fetchall()
        for r in rows:
            title = "Document"
            try:
                # best-effort title extraction
                import json as _json

                md = _json.loads(r["metadata_json"] or "{}")
                title = md.get("title") or md.get("name") or title
            except Exception:
                pass
            con.execute(
                "INSERT INTO fts_all(ref_type, ref_id, campaign_id, session_id, sku, title, body) VALUES (?,?,?,?,?,?,?)",
                ("doc", str(r["doc_id"]), None, None, None, title, r["body"] or ""),
            )

        con.commit()
        return {"ok": True, "fts": True, "indexed": {"docs": len(rows)}}
    finally:
        con.close()
