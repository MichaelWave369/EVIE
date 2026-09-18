from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Depends
from pydantic import BaseModel
from typing import Any, Dict, Optional
import tempfile
from pathlib import Path

from app.security.auth import require_api_key
from app.ingest.pipeline import ingest_text, ingest_file

router = APIRouter(prefix="/v1/ingest", tags=["ingest"])

class IngestTextReq(BaseModel):
    title: str
    text: str
    metadata: Dict[str, Any] = {}

@router.post("/text", dependencies=[Depends(require_api_key)])
def post_text(req: IngestTextReq):
    return ingest_text(req.title, req.text, req.metadata)

@router.post("/file", dependencies=[Depends(require_api_key)])
async def post_file(file: UploadFile = File(...), metadata_json: str = "{}"):
    # metadata_json is a simple JSON string field
    import json
    metadata = json.loads(metadata_json or "{}")
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td) / (file.filename or "upload.bin")
        content = await file.read()
        tmp_path.write_bytes(content)
        return ingest_file(tmp_path, file.filename or "upload.bin", metadata)
