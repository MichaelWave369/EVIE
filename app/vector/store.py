from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import numpy as np
import json, datetime

from app.settings import settings
from app.db.schema import connect

@dataclass
class VectorStore:
    backend: str
    index_path: Path

    # Class-level cache for loaded FAISS index (avoids disk reads on every search)
    _faiss_cache: dict = None

    def __post_init__(self):
        if VectorStore._faiss_cache is None:
            VectorStore._faiss_cache = {"index": None, "meta": None, "mtime": 0}

    @staticmethod
    def from_settings() -> "VectorStore":
        backend = settings.vector_backend.lower().strip()
        index_path = Path(settings.index_dir) / "chunks.index"
        return VectorStore(backend=backend, index_path=index_path)

    # ---------- FAISS ----------
    def _faiss_available(self) -> bool:
        try:
            import faiss  # noqa: F401
            return True
        except Exception:
            return False

    def _load_faiss(self):
        import faiss
        meta_path = self.index_path.with_suffix(".meta.json")
        if self.index_path.exists() and meta_path.exists():
            # Check cache first
            mtime = self.index_path.stat().st_mtime
            cache = VectorStore._faiss_cache
            if cache and cache.get("mtime") == mtime and cache.get("index") is not None:
                return cache["index"], cache["meta"]
            index = faiss.read_index(str(self.index_path))
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            VectorStore._faiss_cache = {"index": index, "meta": meta, "mtime": mtime}
            return index, meta
        index = None
        meta = {"chunk_ids": [], "dims": None}
        return index, meta

    def _save_faiss(self, index, meta):
        import faiss
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.index_path))
        self.index_path.with_suffix(".meta.json").write_text(json.dumps(meta), encoding="utf-8")
        # Invalidate cache so next search picks up new data
        mtime = self.index_path.stat().st_mtime
        VectorStore._faiss_cache = {"index": index, "meta": meta, "mtime": mtime}

    # ---------- LanceDB ----------
    def _lancedb_available(self) -> bool:
        try:
            import lancedb  # noqa: F401
            return True
        except Exception:
            return False

    def _lancedb_table(self):
        import lancedb
        settings.lancedb_dir.mkdir(parents=True, exist_ok=True)
        db = lancedb.connect(str(settings.lancedb_dir))
        try:
            table = db.open_table(settings.lancedb_table)
        except Exception:
            table = None
        return db, table

    def add(self, chunk_ids: List[int], vectors: np.ndarray, model: str) -> None:
        assert len(chunk_ids) == vectors.shape[0]
        dims = int(vectors.shape[1])

        # Always record meta in SQLite (source of truth)
        con = connect()
        now = datetime.datetime.utcnow().isoformat()
        con.executemany(
            "INSERT OR REPLACE INTO vector_meta(chunk_id, model, dims, created_at) VALUES (?,?,?,?)",
            [(int(cid), model, dims, now) for cid in chunk_ids]
        )
        con.commit()
        con.close()

        # LanceDB backend
        if self.backend == "lancedb":
            if not self._lancedb_available():
                raise RuntimeError("EV_VECTOR_BACKEND=lancedb but 'lancedb' is not installed. pip install lancedb pyarrow")
            import numpy as _np
            db, table = self._lancedb_table()

            # Normalize for cosine similarity
            vecs = vectors.astype(_np.float32)
            def _norm(a):
                n = _np.linalg.norm(a, axis=1, keepdims=True) + 1e-9
                return a / n
            vecs = _norm(vecs)

            rows = []
            for cid, v in zip(chunk_ids, vecs):
                rows.append({
                    "chunk_id": int(cid),
                    "vector": v.tolist(),
                    "model": model,
                    "dims": dims,
                    "created_at": now
                })

            if table is None:
                table = db.create_table(settings.lancedb_table, data=rows)
            else:
                table.add(rows)
            return

        # FAISS backend
        if self.backend == "faiss" and self._faiss_available():
            import faiss
            index, meta = self._load_faiss()
            if index is None:
                index = faiss.IndexFlatIP(dims)
                meta["dims"] = dims
            elif meta.get("dims") != dims:
                raise ValueError(f"Vector dims changed: index has {meta.get('dims')} but new vectors have {dims}")
            faiss.normalize_L2(vectors)
            index.add(vectors.astype(np.float32))
            meta["chunk_ids"].extend([int(c) for c in chunk_ids])
            self._save_faiss(index, meta)
            return

        # Numpy fallback: store in .npz + meta
        np_path = self.index_path.with_suffix(".npz")
        meta_path = self.index_path.with_suffix(".meta.json")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        if np_path.exists() and meta_path.exists():
            data = np.load(np_path)
            existing = data["vectors"]
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            vec_all = np.vstack([existing, vectors])
            meta["chunk_ids"].extend([int(c) for c in chunk_ids])
            meta["dims"] = dims
        else:
            vec_all = vectors
            meta = {"chunk_ids": [int(c) for c in chunk_ids], "dims": dims}

        np.savez_compressed(np_path, vectors=vec_all.astype(np.float32))
        meta_path.write_text(json.dumps(meta), encoding="utf-8")

    def search(self, query_vec: np.ndarray, top_k: int = 8) -> List[Tuple[int, float]]:
        # returns list of (chunk_id, score)
        q = query_vec.astype(np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)

        if self.backend == "lancedb":
            if not self._lancedb_available():
                raise RuntimeError("EV_VECTOR_BACKEND=lancedb but 'lancedb' is not installed. pip install lancedb pyarrow")
            import numpy as _np
            db, table = self._lancedb_table()
            if table is None:
                return []
            # normalize
            n = _np.linalg.norm(q, axis=1, keepdims=True) + 1e-9
            qn = (q / n)[0].tolist()
            res = table.search(qn).limit(int(top_k)).to_list()
            out = []
            for r in res:
                out.append((int(r["chunk_id"]), float(r.get("_distance", 0.0))))
            # LanceDB uses distance by default; convert to similarity-ish if possible.
            # If it's cosine distance, similarity = 1 - distance.
            out2=[]
            for cid, dist in out:
                sim = 1.0 - dist
                out2.append((cid, sim))
            return out2

        if self.backend == "faiss" and self._faiss_available():
            import faiss
            index, meta = self._load_faiss()
            if index is None or len(meta.get("chunk_ids", [])) == 0:
                return []
            faiss.normalize_L2(q)
            scores, idxs = index.search(q, int(top_k))
            out = []
            for i, s in zip(idxs[0].tolist(), scores[0].tolist()):
                if i < 0:
                    continue
                out.append((int(meta["chunk_ids"][i]), float(s)))
            return out

        # numpy fallback
        meta_path = self.index_path.with_suffix(".meta.json")
        np_path = self.index_path.with_suffix(".npz")
        if not (meta_path.exists() and np_path.exists()):
            return []
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        data = np.load(np_path)
        vecs = data["vectors"].astype(np.float32)

        def norm(a):
            n = np.linalg.norm(a, axis=1, keepdims=True) + 1e-9
            return a / n

        qq = norm(q)
        vv = norm(vecs)
        sims = (vv @ qq.T).reshape(-1)
        top_idx = np.argsort(-sims)[:int(top_k)]
        return [(int(meta["chunk_ids"][i]), float(sims[i])) for i in top_idx]
