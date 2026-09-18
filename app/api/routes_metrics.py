from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from pathlib import Path
import datetime

from app.security.auth import require_api_key
from app.db import queries
from app.modules.metrics_optimizer import summarize_rows, recommendations
import csv, json

router = APIRouter(prefix="/v1/metrics", tags=["metrics"])

class AnalyzeReq(BaseModel):
    run_id: Optional[int] = None
    topic: str = "metrics"
    csv_path: Optional[str] = None
    csv_text: Optional[str] = None

def _read_csv_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

@router.post("/import")
async def import_metrics(
    file: UploadFile = File(...),
    source: Optional[str] = Form(None),
    api_key: str = Depends(require_api_key),
):
    base = Path("data/metrics_uploads")
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fname = file.filename or f"metrics_{ts}.csv"
    out = base / f"{ts}_{fname}"
    content = await file.read()
    out.write_bytes(content)
    rid = queries.create_metrics_run(source, fname, str(out), summary={})
    queries.log_audit("user", "metrics_import", "metrics_run", str(rid), {"source": source, "path": str(out)})
    return {"run_id": rid, "path": str(out)}

@router.post("/analyze")
def analyze_metrics(req: AnalyzeReq, api_key: str = Depends(require_api_key)):
    csv_text = req.csv_text
    if req.run_id is not None:
        runs = {r["run_id"]: r for r in queries.list_metrics_runs(250)}
        run = runs.get(int(req.run_id))
        if not run:
            raise HTTPException(status_code=404, detail="run_id not found")
        csv_text = _read_csv_text(Path(run["path"]))
    elif req.csv_path:
        p = Path(req.csv_path)
        if not p.exists():
            raise HTTPException(status_code=400, detail="csv_path not found")
        csv_text = _read_csv_text(p)

    if not csv_text:
        raise HTTPException(status_code=400, detail="No CSV provided")

    rows=[]
    reader = csv.DictReader(csv_text.splitlines())
    for r in reader:
        rows.append(r)

    summary = summarize_rows(rows)
    recs = recommendations(summary)

    payload = {"summary": summary, "recommendations": recs, "rows": len(rows)}
    if req.run_id is not None:
        queries.update_metrics_run(int(req.run_id), payload)

    queries.log_audit("user", "metrics_analyze", "metrics_run", str(req.run_id) if req.run_id else None, payload)
    return payload

@router.get("/runs")
def list_runs(limit: int = 25, api_key: str = Depends(require_api_key)):
    return {"runs": queries.list_metrics_runs(limit=int(limit))}
