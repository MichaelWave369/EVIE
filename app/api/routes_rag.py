from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.security.auth import require_api_key
from app.rag.composer import answer

router = APIRouter(prefix="/v1/rag", tags=["rag"])

class RagReq(BaseModel):
    question: str
    top_k: int = 8

@router.post("/answer", dependencies=[Depends(require_api_key)])
def rag_answer(req: RagReq):
    return answer(req.question, top_k=req.top_k)
