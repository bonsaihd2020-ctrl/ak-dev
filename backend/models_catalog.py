from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import requests

from config import DEFAULT_PROVIDERS


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    is_free: bool = False
    tool_calling_supported: bool = True
    context_window: int = 0
    description: str = ""


BUILTIN_MODELS: Dict[str, List[Dict[str, Any]]] = {
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "is_free": False, "tool_calling": True, "ctx": 128000},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "is_free": False, "tool_calling": True, "ctx": 128000},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "is_free": False, "tool_calling": True, "ctx": 128000},
        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "is_free": False, "tool_calling": True, "ctx": 16385},
    ],
    "anthropic": [
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "is_free": False, "tool_calling": True, "ctx": 200000},
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "is_free": False, "tool_calling": True, "ctx": 200000},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "is_free": False, "tool_calling": True, "ctx": 200000},
        {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "is_free": False, "tool_calling": True, "ctx": 200000},
    ],
    "deepseek": [
        {"id": "deepseek-chat", "name": "DeepSeek V3", "is_free": False, "tool_calling": True, "ctx": 64000},
        {"id": "deepseek-reasoner", "name": "DeepSeek R1", "is_free": False, "tool_calling": True, "ctx": 64000},
    ],
    "groq": [
        {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "is_free": True, "tool_calling": True, "ctx": 128000},
        {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant", "is_free": True, "tool_calling": True, "ctx": 128000},
        {"id": "gemma2-9b-it", "name": "Gemma 2 9B", "is_free": True, "tool_calling": False, "ctx": 8192},
        {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "is_free": True, "tool_calling": True, "ctx": 32768},
    ],
    "openrouter": [
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B (Free)", "is_free": True, "tool_calling": True, "ctx": 128000},
        {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash (Free)", "is_free": True, "tool_calling": True, "ctx": 128000},
        {"id": "qwen/qwen-2.5-72b-instruct:free", "name": "Qwen 2.5 72B (Free)", "is_free": True, "tool_calling": True, "ctx": 32768},
        {"id": "deepseek/deepseek-chat-v3-0324:free", "name": "DeepSeek V3 (Free)", "is_free": True, "tool_calling": True, "ctx": 64000},
        {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4", "is_free": False, "tool_calling": True, "ctx": 200000},
        {"id": "openai/gpt-4o", "name": "GPT-4o", "is_free": False, "tool_calling": True, "ctx": 128000},
        {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "is_free": False, "tool_calling": True, "ctx": 128000},
    ],
    "together": [
        {"id": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "name": "Llama 3.3 70B Turbo", "is_free": False, "tool_calling": True, "ctx": 128000},
        {"id": "Qwen/Qwen2.5-72B-Instruct-Turbo", "name": "Qwen 2.5 72B Turbo", "is_free": False, "tool_calling": True, "ctx": 32768},
        {"id": "deepseek-ai/DeepSeek-V3", "name": "DeepSeek V3", "is_free": False, "tool_calling": True, "ctx": 64000},
    ],
    "ollama": [],
}


def _fetch_openrouter_models() -> List[Dict[str, Any]]:
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            models = []
            for m in data:
                mid = m.get("id", "")
                pricing = m.get("pricing", {})
                prompt_price = float(pricing.get("prompt", "0") or "0")
                completion_price = float(pricing.get("completion", "0") or "0")
                is_free = ":free" in mid or (prompt_price == 0 and completion_price == 0)
                models.append({
                    "id": mid,
                    "name": m.get("name", mid),
                    "is_free": is_free,
                    "tool_calling": True,
                    "ctx": m.get("context_length", 0),
                })
            return models
    except Exception:
        pass
    return []


def _fetch_ollama_models() -> List[Dict[str, Any]]:
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("models", [])
            models = []
            for m in data:
                models.append({
                    "id": m.get("name", ""),
                    "name": m.get("name", ""),
                    "is_free": True,
                    "tool_calling": False,
                    "ctx": 0,
                })
            return models
    except Exception:
        pass
    return []


def get_models_for_provider(provider_id: str, free_only: bool = False) -> List[ModelInfo]:
    if provider_id == "openrouter":
        models = _fetch_openrouter_models()
        if not models:
            models = BUILTIN_MODELS.get("openrouter", [])
    elif provider_id == "ollama":
        models = _fetch_ollama_models()
        if not models:
            models = BUILTIN_MODELS.get("ollama", [])
    else:
        models = BUILTIN_MODELS.get(provider_id, [])

    result = []
    for m in models:
        if free_only and not m.get("is_free", False):
            continue
        result.append(ModelInfo(
            id=m["id"],
            name=m.get("name", m["id"]),
            provider=provider_id,
            is_free=m.get("is_free", False),
            tool_calling_supported=m.get("tool_calling", True),
            context_window=m.get("ctx", 0),
        ))
    return result


def get_all_providers_with_models(free_only: bool = False) -> List[Dict[str, Any]]:
    result = []
    for p in DEFAULT_PROVIDERS:
        models = get_models_for_provider(p["id"], free_only=free_only)
        result.append({
            "provider": p,
            "models": [m.__dict__ for m in models],
        })
    return result
