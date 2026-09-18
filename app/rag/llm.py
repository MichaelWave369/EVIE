from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
from app.settings import settings

@dataclass
class LLM:
    backend: str
    model: str

    @staticmethod
    def from_settings() -> "LLM":
        b = settings.llm_backend.lower().strip()
        if b == "ollama":
            return OllamaLLM(settings.ollama_chat_model)
        if b == "openai":
            key = settings.openai_api_key
            if not key:
                raise ValueError("EV_OPENAI_API_KEY is not set. Add it to your .env file.")
            return OpenAILLM(model=settings.openai_model, api_key=key)
        if b == "anthropic":
            key = settings.anthropic_api_key
            if not key:
                raise ValueError("EV_ANTHROPIC_API_KEY is not set. Add it to your .env file.")
            return AnthropicLLM(model=settings.anthropic_model, api_key=key)
        if b == "none":
            return NoopLLM()
        raise ValueError(f"Unknown EV_LLM_BACKEND: {settings.llm_backend}. Options: ollama | openai | anthropic | none")

    def chat(self, messages: List[Dict[str, str]]) -> str:
        raise NotImplementedError


class NoopLLM(LLM):
    def __init__(self):
        super().__init__(backend="none", model="none")

    def chat(self, messages):
        return (
            "LLM backend is disabled (EV_LLM_BACKEND=none).\n\n"
            "To enable AI generation, set one of these in your .env file:\n"
            "  EV_LLM_BACKEND=openai    (also set EV_OPENAI_API_KEY=sk-...)\n"
            "  EV_LLM_BACKEND=anthropic  (also set EV_ANTHROPIC_API_KEY=sk-ant-...)\n"
            "  EV_LLM_BACKEND=ollama     (install Ollama locally first)"
        )


class OllamaLLM(LLM):
    def __init__(self, model: str):
        super().__init__(backend="ollama", model=model)

    def chat(self, messages: List[Dict[str, str]]) -> str:
        import requests
        url = settings.ollama_base_url.rstrip("/") + "/api/chat"
        timeout = int(settings.ollama_timeout)
        r = requests.post(url, json={"model": self.model, "messages": messages, "stream": False}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"]


class OpenAILLM(LLM):
    def __init__(self, model: str, api_key: str):
        super().__init__(backend="openai", model=model)
        self._api_key = api_key

    def chat(self, messages: List[Dict[str, str]]) -> str:
        import requests
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]


class AnthropicLLM(LLM):
    def __init__(self, model: str, api_key: str):
        super().__init__(backend="anthropic", model=model)
        self._api_key = api_key

    def chat(self, messages: List[Dict[str, str]]) -> str:
        import requests
        system_msgs = [m["content"] for m in messages if m["role"] == "system"]
        user_msgs = [m for m in messages if m["role"] != "system"]
        system_prompt = "\n".join(system_msgs) if system_msgs else None

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": user_msgs,
        }
        if system_prompt:
            payload["system"] = system_prompt

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        return data["content"][0]["text"]
