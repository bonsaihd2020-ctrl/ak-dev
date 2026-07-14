from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEFAULT_PROVIDERS: List[Dict] = [
    {
        "id": "openai",
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "auth_type": "api_key",
        "supports_browser_login": False,
        "icon": "openai",
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "auth_type": "api_key",
        "supports_browser_login": False,
        "icon": "anthropic",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "auth_type": "api_key",
        "supports_browser_login": False,
        "icon": "deepseek",
    },
    {
        "id": "groq",
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "auth_type": "api_key",
        "supports_browser_login": False,
        "icon": "groq",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "auth_type": "api_key",
        "supports_browser_login": False,
        "icon": "openrouter",
    },
    {
        "id": "together",
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "auth_type": "api_key",
        "supports_browser_login": False,
        "icon": "together",
    },
    {
        "id": "ollama",
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "auth_type": "none",
        "supports_browser_login": False,
        "icon": "ollama",
    },
]

SEARCH_BACKENDS = ["tavily", "brave"]

CONTAINER_NAME = "devin-sandbox"
CONTAINER_IMAGE = "devin-sandbox:latest"
NOVNC_PORT = 6080
VNC_PORT = 5900
SANDBOX_WORKSPACE = "/workspace"
LOCAL_WORKSPACE_SYNC = os.path.join(os.path.expanduser("~"), ".devin-clone", "workspace-sync")

MAX_AGENT_ITERATIONS = 30
AGENT_RETRY_BUDGET = 3

WS_PORT = 8765
API_HOST = "127.0.0.1"
API_PORT = 18900
