from __future__ import annotations
from typing import Any, Dict, List, Tuple
import math

from app.vector.embeddings import EmbeddingClient
from app.vector.store import VectorStore
from app.db import queries
from app.settings import settings

FIB_NUMS = [1,2,3,5,8,13,21,34,55,89,144,233]

def simple_chunk(text: str, max_chars: int = 1200, overlap: int = 120) -> List[Dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return []
    chunks = []
    i = 0
    idx = 0
    while i < len(t):
        chunk = t[i:i+max_chars]
        chunks.append({"chunk_index": idx, "text": chunk, "token_count": max(1, len(chunk)//4)})
        idx += 1
        i += max_chars - overlap
    return chunks

def harmonic_score(domain_id: int | None, phase_id: int | None, state_id: int | None, lens_id: int | None) -> float:
    # 369 / Phi / Fibonacci alignment bonus in [0, ~1.2]
    d = int(domain_id or 0)
    p = int(phase_id or 0)
    s = int(state_id or 0)
    l = int(lens_id or 0)
    total = d + p + s + l

    vib369 = 1.0 if (total % 9 == 0 and total > 0) else 0.0

    # phi proportion between lens and the rest
    phi_weight = (0.618 * l) + (0.382 * (d + p + s))
    phi_norm = max(0.0, min(1.0, phi_weight / 50.0))

    # distance to nearest fibonacci number
    fib_dist = min(abs(total - f) for f in FIB_NUMS) if total > 0 else 999
    fib_bonus = 1.0 / (fib_dist + 1.0)

    return (0.40 * vib369) + (0.40 * phi_norm) + (0.20 * fib_bonus)

def retrieve(query: str, top_k: int = 8) -> List[Dict[str, Any]]:
    emb = EmbeddingClient.from_settings()
    vs = VectorStore.from_settings()

    qv = emb.embed_texts([query])[0]
    # Grab more raw candidates, then optionally rerank.
    raw_k = int(max(top_k, 1) * (3 if settings.rerank_harmonic else 1))
    hits = vs.search(qv, top_k=raw_k)
    if not hits:
        return []

    chunk_ids = [cid for cid, _ in hits]
    score_map = {int(cid): float(score) for cid, score in hits}

    rows = queries.get_chunks_with_docs(chunk_ids)

    out = []
    for r in rows:
        cid = int(r["chunk_id"])
        base = float(score_map.get(cid, 0.0))
        h = harmonic_score(r.get("domain_id"), r.get("phase_id"), r.get("state_id"), r.get("lens_id"))
        # Combine base similarity with harmonic bonus. Weight controls influence.
        final = (1.0 - settings.rerank_weight) * base + settings.rerank_weight * h
        out.append({
            "chunk_id": cid,
            "score": float(final),
            "score_base": float(base),
            "score_harmonic": float(h),
            "text": r.get("chunk_text") or "",
            "doc_id": int(r.get("doc_id") or 0),
            "canonical_key": r.get("canonical_key"),
            "domain_id": r.get("domain_id"),
            "phase_id": r.get("phase_id"),
            "state_id": r.get("state_id"),
            "lens_id": r.get("lens_id"),
            "metadata": r.get("metadata") or {},
        })

    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:int(top_k)]
