SYSTEM_RAG = """You are an assistant that must stay grounded in the provided context.
If the context is insufficient, say what is missing and suggest what to ingest next.
Do NOT fabricate citations. Prefer short, actionable answers."""

RAG_TEMPLATE = """User question:
{question}

Context snippets (most relevant first):
{context}

Answer (grounded):
"""
