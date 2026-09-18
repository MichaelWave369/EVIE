from __future__ import annotations
from typing import Dict, Any, List
from app.rag.retriever import retrieve
from app.rag.llm import LLM
from app.rag.prompts import SYSTEM_RAG, RAG_TEMPLATE

def answer(question: str, top_k: int = 8) -> Dict[str, Any]:
    hits = retrieve(question, top_k=top_k)
    context = "\n\n---\n\n".join([f"[chunk {h['chunk_id']} score={h['score']:.3f}]\n{h['text']}" for h in hits])

    llm = LLM.from_settings()
    messages = [
        {"role": "system", "content": SYSTEM_RAG},
        {"role": "user", "content": RAG_TEMPLATE.format(question=question, context=context)}
    ]
    resp = llm.chat(messages)
    return {"answer": resp, "sources": [{"chunk_id": h["chunk_id"], "score": h["score"]} for h in hits]}
