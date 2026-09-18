from __future__ import annotations
import datetime, json, os, shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.settings import settings
from app.db import queries
from app.taxonomy.enums import DOMAINS, PHASES, STATES, LENSES
from app.taxonomy.cell20736 import make_key
from app.ingest.extract import extract_text_from_file
from app.vector.embeddings import EmbeddingClient
from app.vector.store import VectorStore
from app.rag.retriever import simple_chunk

def _auto_tag(metadata: Dict[str, Any]) -> Tuple[int, int, int, int]:
    # Local-first heuristic defaults.
    # You can override by passing explicit ids in metadata.
    domain_id = int(metadata.get("domain_id", 12))  # Meta by default
    phase_id = int(metadata.get("phase_id", 1))    # Input
    state_id = int(metadata.get("state_id", 3))    # Emerging
    lens_id = int(metadata.get("lens_id", 7))      # Informational
    return domain_id, phase_id, state_id, lens_id

def ingest_text(title: str, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    domain_id, phase_id, state_id, lens_id = _auto_tag(metadata)
    ck = make_key(domain_id, phase_id, state_id, lens_id)
    source_id = queries.upsert_source("text", None, title)
    doc_id = queries.insert_document(source_id, text, metadata, domain_id, phase_id, state_id, lens_id, ck)

    chunks = simple_chunk(text)
    chunk_ids = queries.insert_chunks(doc_id, chunks)

    emb = EmbeddingClient.from_settings()
    vs = VectorStore.from_settings()
    vector_status = "ok"
    vector_error = None
    try:
        vectors = emb.embed_texts([c["text"] for c in chunks])
        vs.add(chunk_ids=chunk_ids, vectors=vectors, model=emb.model_name)
    except Exception as e:
        vector_status = "error"
        vector_error = str(e)

    queries.log_audit("system", "ingest_text", "document", str(doc_id), {"title": title, "chunks": len(chunk_ids), "canonical_key": ck, "vector_status": vector_status, "vector_error": vector_error})
    return {"doc_id": doc_id, "chunk_count": len(chunk_ids), "canonical_key": ck, "vector_status": vector_status, "vector_error": vector_error}

def ingest_file(upload_path: Path, original_filename: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    # store file locally
    settings.vault_files_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = original_filename.replace("..", "_").replace("/", "_").replace("\\", "_")
    dest = settings.vault_files_dir / f"{ts}__{safe_name}"
    shutil.copyfile(str(upload_path), str(dest))

    kind, text = extract_text_from_file(dest)
    source_id = queries.upsert_source("file", str(dest), original_filename)

    domain_id, phase_id, state_id, lens_id = _auto_tag(metadata)
    ck = make_key(domain_id, phase_id, state_id, lens_id)

    meta2 = dict(metadata)
    meta2.update({"filename": original_filename, "stored_path": str(dest), "kind": kind})
    doc_id = queries.insert_document(source_id, text, meta2, domain_id, phase_id, state_id, lens_id, ck)

    chunks = simple_chunk(text)
    chunk_ids = queries.insert_chunks(doc_id, chunks)

    emb = EmbeddingClient.from_settings()
    vs = VectorStore.from_settings()
    vector_status = "ok"
    vector_error = None
    try:
        vectors = emb.embed_texts([c["text"] for c in chunks])
        vs.add(chunk_ids=chunk_ids, vectors=vectors, model=emb.model_name)
    except Exception as e:
        vector_status = "error"
        vector_error = str(e)

    queries.log_audit("system", "ingest_file", "document", str(doc_id), {"file": original_filename, "chunks": len(chunk_ids), "canonical_key": ck, "vector_status": vector_status, "vector_error": vector_error})
    return {"doc_id": doc_id, "chunk_count": len(chunk_ids), "canonical_key": ck, "stored_path": str(dest), "vector_status": vector_status, "vector_error": vector_error}
