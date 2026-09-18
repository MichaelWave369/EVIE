#!/usr/bin/env python
from __future__ import annotations
import argparse, csv, json, datetime
from pathlib import Path
from typing import Dict, Any, List

from app.settings import settings
from app.db.schema import connect
from app.db import queries
from app.vector.embeddings import EmbeddingClient
from app.vector.store import VectorStore
from app.rag.retriever import simple_chunk

def upsert_doc(con, title: str, canonical_key: str, content: str, meta: Dict[str, Any], domain: int, phase: int, state: int, lens: int) -> int:
    now = datetime.datetime.utcnow().isoformat()
    cur = con.execute(
        "INSERT INTO documents(title, canonical_key, source_type, source_path, content, metadata_json, domain_id, phase_id, state_id, lens_id, created_at)\n"
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, canonical_key, "cell20736", None, content, json.dumps(meta, ensure_ascii=False), domain, phase, state, lens, now)
    )
    return int(cur.lastrowid)

def main():
    ap = argparse.ArgumentParser(description="Ingest Cell20736.csv rows as searchable ontology docs (local-only)")
    ap.add_argument("--csv", default="Cell20736.csv", help="Path to Cell20736.csv")
    ap.add_argument("--limit", type=int, default=0, help="Optional limit for quick tests")
    ap.add_argument("--batch", type=int, default=128, help="Embedding batch size")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    con = connect()
    # If already ingested, bail unless user wants to re-run.
    existing = con.execute("SELECT COUNT(1) AS n FROM documents WHERE source_type='cell20736'").fetchone()[0]
    if existing and existing > 0:
        print(f"Found {existing} existing cell20736 docs. (Skip) If you want a re-run, delete them from the DB first.")
        con.close()
        return

    emb = EmbeddingClient.from_settings()
    vs = VectorStore.from_settings()

    rows_buf = []
    chunks_buf = []
    chunk_meta = []
    chunk_ids = []
    vectors_buf = []

    def flush(batch_chunks):
        if not batch_chunks:
            return
        texts = [c["text"] for c in batch_chunks]
        vecs = emb.embed_texts(texts)
        return vecs

    total = 0
    created_chunks = 0

    with csv_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            total += 1
            if args.limit and total > args.limit:
                break

            canonical = r.get("CanonicalKey") or r.get("canonical") or ""
            if not canonical:
                continue

            domain = int(r.get("DomainID") or r.get("domain") or 0)
            phase = int(r.get("PhaseID") or r.get("phase") or 0)
            state = int(r.get("StateID") or r.get("state") or 0)
            lens = int(r.get("LensID") or r.get("lens") or 0)

            allowed = r.get("AllowedOutputs") or r.get("allowed") or ""
            gate = r.get("GateProfile") or r.get("gate") or ""
            safety = int(r.get("SafetyTier") or r.get("safety") or 0)

            title = f"Cell {canonical} (D{domain} P{phase} S{state} L{lens})"
            text = (
                f"Ontology Cell: {canonical}\n"
                f"Domain={domain} Phase={phase} State={state} Lens={lens}\n"
                f"AllowedOutputs={allowed}\n"
                f"GateProfile={gate}\n"
                f"SafetyTier={safety}\n"
            )

            doc_key = f"CELL:{canonical}"
            doc_id = upsert_doc(con, title, doc_key, text, {"allowed": allowed, "gate": gate, "safety": safety}, domain, phase, state, lens)

            # single chunk (or two) for search
            chunks = simple_chunk(text, max_chars=900, overlap=80)
            for c in chunks:
                cur = con.execute(
                    "INSERT INTO chunks(doc_id, chunk_index, chunk_text, token_count) VALUES (?,?,?,?)",
                    (doc_id, int(c["chunk_index"]), c["text"], int(c["token_count"]))
                )
                chunk_id = int(cur.lastrowid)
                chunks_buf.append({"text": c["text"], "chunk_id": chunk_id})
                chunk_ids.append(chunk_id)

            if len(chunks_buf) >= args.batch:
                con.commit()
                vecs = flush([{"text": x["text"]} for x in chunks_buf])
                vs.add(chunk_ids, vecs, model=settings.ollama_embed_model if settings.embed_backend=="ollama" else settings.st_model)
                created_chunks += len(chunks_buf)
                print(f"Embedded {created_chunks} chunks...")
                chunks_buf.clear()
                chunk_ids.clear()

    # final flush
    con.commit()
    if chunks_buf:
        vecs = flush([{"text": x["text"]} for x in chunks_buf])
        vs.add(chunk_ids, vecs, model=settings.ollama_embed_model if settings.embed_backend=="ollama" else settings.st_model)
        created_chunks += len(chunks_buf)
        chunks_buf.clear()
        chunk_ids.clear()

    con.commit()
    con.close()
    print(f"Done. Ingested {total} rows and embedded {created_chunks} chunks.")

if __name__ == "__main__":
    main()
