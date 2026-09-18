from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EV_", env_file=".env", extra="ignore")

    # Local-only storage
    data_dir: Path = Field(default=Path("./data"))
    db_path: Path = Field(default=Path("./data/embervault.db"))
    vault_files_dir: Path = Field(default=Path("./data/vault_files"))
    index_dir: Path = Field(default=Path("./data/indexes"))
    gumroad_dir: Path = Field(default=Path("./data/gumroad"))

    # Workflow registry (TIEKAT-style recipes)
    workflow_registry_path: Path = Field(default=Path("./configs/workflows.json"))

    # Swarm mode (TIEKAT-style director)
    swarm_enabled: bool = Field(default=True)
    swarm_director_backend: str = Field(default="heuristic")  # heuristic | ollama
    agent_memory_dir: Path = Field(default=Path("./data/agent_memory"))

    # Full-text search (SQLite FTS5 if available)
    fts_enabled: bool = Field(default=True)

    # Sandbox execution (best-effort isolation for generated code checks)
    sandbox_enabled: bool = Field(default=True)
    sandbox_mode: str = Field(default="subprocess")  # subprocess | docker
    sandbox_timeout_seconds: int = Field(default=30)
    sandbox_work_root: Path = Field(default=Path("./data/sandboxes"))
    sandbox_env_allowlist: str = Field(default="PATH,PYTHONPATH")
    sandbox_docker_image: str = Field(default="python:3.11-slim")
    sandbox_docker_network: str = Field(default="none")
    sandbox_docker_cpus: str = Field(default="0.50")
    sandbox_docker_memory: str = Field(default="512m")
    sandbox_docker_read_only: bool = Field(default=False)

    # API auth (local network only unless you expose it)
    api_key: str = Field(default="change-me")

    # Background automation (optional)
    worker_autorun: bool = Field(default=False)
    worker_interval_seconds: int = Field(default=300)

    # Embeddings (local or cloud)
    embed_backend: str = Field(default="hash")  # hash | ollama | openai | sentence_transformers
    ollama_base_url: str = Field(default="http://127.0.0.1:11434")
    ollama_embed_model: str = Field(default="nomic-embed-text")

    st_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    st_model_local_path: str | None = Field(default=None)

    # LLM (local or cloud)
    llm_backend: str = Field(default="ollama")  # ollama | openai | anthropic | none
    ollama_chat_model: str = Field(default="llama3.1")
    ollama_timeout: int = Field(default=600)  # seconds; 120 was too low for long ebook generation

    # OpenAI / Anthropic (cloud options — no local GPU required!)
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4o-mini")
    anthropic_api_key: str | None = Field(default=None)
    anthropic_model: str = Field(default="claude-3-5-haiku-20241022")

    # Vector index (local)
    vector_backend: str = Field(default="faiss")  # faiss | numpy | lancedb
    lancedb_dir: Path = Field(default=Path("./data/indexes/lancedb"))
    lancedb_table: str = Field(default="chunks")

    # Retrieval alignment (369 / phi / fib)
    rerank_harmonic: bool = Field(default=True)
    rerank_weight: float = Field(default=0.30)  # 0..1 how much harmonic score influences final rank

    # Artifact safety (local-only guardrails)
    artifact_max_bytes: int = Field(default=50_000_000)  # 50MB per file
    artifact_allowed_exts: str = Field(default='.md,.txt,.json,.csv,.pdf,.docx,.png,.jpg,.jpeg,.zip,.html,.css,.js')

    # Media ingestion (optional, local)
    ocr_backend: str = Field(default="none")  # none | tesseract
    transcribe_backend: str = Field(default="none")  # none | whisper | faster_whisper
    whisper_model: str = Field(default="base")  # tiny | base | small | medium | large-v3 (depending on backend)
    ffmpeg_bin: str = Field(default="ffmpeg")  # path to ffmpeg if needed

settings = Settings()
