from __future__ import annotations
import json
import time
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Generator

from keystore import get_keystore


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, window_size: float = 120.0) -> None:
        self._state = self.CLOSED
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._window_size = window_size
        self._last_failure_time: float = 0
        self._last_success_time: float = 0
        self._lock = threading.Lock()
        self._failures: List[float] = []

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time > self._recovery_timeout:
                    self._state = self.HALF_OPEN
            return self._state

    def record_success(self) -> None:
        with self._lock:
            self._last_success_time = time.time()
            self._state = self.CLOSED
            self._failure_count = 0
            self._failures.clear()

    def record_failure(self) -> None:
        with self._lock:
            now = time.time()
            self._failures.append(now)
            self._failures = [t for t in self._failures if now - t < self._window_size]
            self._failure_count = len(self._failures)
            self._last_failure_time = now
            if self._failure_count >= self._failure_threshold:
                self._state = self.OPEN

    def can_request(self) -> bool:
        state = self.state
        return state != self.OPEN


class RetryHandler:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        delay = self._base_delay * (2 ** attempt)
        return min(delay, self._max_delay)

    def is_retryable(self, error: Exception) -> bool:
        error_str = str(error).lower()
        retryable_patterns = [
            "timeout", "rate limit", "429", "502", "503", "504",
            "connection", "network", "overloaded", "capacity",
        ]
        return any(p in error_str for p in retryable_patterns)

    def is_rate_limit(self, error: Exception) -> bool:
        error_str = str(error).lower()
        return "429" in error_str or "rate limit" in error_str

    def get_rate_limit_delay(self, error: Exception) -> float:
        error_str = str(error)
        if "retry-after" in error_str.lower():
            try:
                idx = error_str.lower().index("retry-after")
                num_str = error_str[idx + 11:idx + 20].strip().split()[0]
                return float(num_str)
            except (ValueError, IndexError):
                pass
        return 30.0


class LLMProvider(ABC):
    def __init__(self, provider_id: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.provider_id = provider_id
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def chat(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None, stream: bool = False) -> Dict[str, Any]:
        ...

    @abstractmethod
    def chat_stream(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None) -> Generator[Dict[str, Any], None, None]:
        ...

    @abstractmethod
    def test_connection(self, model: str) -> Dict[str, Any]:
        ...


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, provider_id: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        super().__init__(provider_id, api_key, base_url)
        self._client = None
        self._breaker = CircuitBreaker()
        self._retry = RetryHandler()

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            kwargs = {"api_key": self.api_key or "dummy"}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def chat(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None, stream: bool = False) -> Dict[str, Any]:
        if not self._breaker.can_request():
            raise Exception(f"Circuit breaker open for {self.provider_id}. Too many failures. Wait and try again.")

        last_error = None
        for attempt in range(self._retry._max_retries + 1):
            try:
                client = self._get_client()
                kwargs: Dict[str, Any] = {"model": model, "messages": messages}
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                response = client.chat.completions.create(**kwargs)
                self._breaker.record_success()
                choice = response.choices[0]
                result: Dict[str, Any] = {
                    "role": "assistant",
                    "content": choice.message.content or "",
                    "tool_calls": [],
                }
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        result["tool_calls"].append({
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        })
                return result
            except Exception as e:
                last_error = e
                self._breaker.record_failure()
                if attempt < self._retry._max_retries and self._retry.is_retryable(e):
                    if self._retry.is_rate_limit(e):
                        delay = self._retry.get_rate_limit_delay(e)
                    else:
                        delay = self._retry.get_delay(attempt)
                    time.sleep(delay)
                    continue
                raise

        raise last_error or Exception(f"All retries exhausted for {self.provider_id}")

    def chat_stream(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None) -> Generator[Dict[str, Any], None, None]:
        if not self._breaker.can_request():
            yield {"type": "error", "content": f"Circuit breaker open for {self.provider_id}"}
            return

        last_error = None
        for attempt in range(self._retry._max_retries + 1):
            try:
                client = self._get_client()
                kwargs: Dict[str, Any] = {"model": model, "messages": messages, "stream": True}
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                stream = client.chat.completions.create(**kwargs)
                collected_tool_calls: Dict[int, Dict] = {}
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield {"type": "content", "content": delta.content}
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in collected_tool_calls:
                                collected_tool_calls[idx] = {"id": tc.id or "", "function": {"name": "", "arguments": ""}}
                            if tc.id:
                                collected_tool_calls[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    collected_tool_calls[idx]["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    collected_tool_calls[idx]["function"]["arguments"] += tc.function.arguments
                    if chunk.choices[0].finish_reason == "stop":
                        break
                self._breaker.record_success()
                if collected_tool_calls:
                    yield {"type": "tool_calls", "tool_calls": list(collected_tool_calls.values())}
                return
            except Exception as e:
                last_error = e
                self._breaker.record_failure()
                if attempt < self._retry._max_retries and self._retry.is_retryable(e):
                    if self._retry.is_rate_limit(e):
                        delay = self._retry.get_rate_limit_delay(e)
                    else:
                        delay = self._retry.get_delay(attempt)
                    time.sleep(delay)
                    continue
                yield {"type": "error", "content": str(e)}
                return

        yield {"type": "error", "content": str(last_error)}

    def test_connection(self, model: str) -> Dict[str, Any]:
        try:
            result = self.chat([{"role": "user", "content": "Say hello in one word."}], model=model)
            return {"success": True, "response": result.get("content", "")[:100], "circuit_state": self._breaker.state}
        except Exception as e:
            return {"success": False, "error": str(e), "circuit_state": self._breaker.state}


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        super().__init__("anthropic", api_key, base_url or "https://api.anthropic.com")
        self._client = None
        self._breaker = CircuitBreaker()
        self._retry = RetryHandler()

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic
            kwargs = {"api_key": self.api_key or "dummy"}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = Anthropic(**kwargs)
        return self._client

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        converted = []
        for t in tools:
            func = t.get("function", {})
            converted.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {}),
            })
        return converted

    def chat(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None, stream: bool = False) -> Dict[str, Any]:
        if not self._breaker.can_request():
            raise Exception(f"Circuit breaker open for anthropic. Too many failures.")

        last_error = None
        for attempt in range(self._retry._max_retries + 1):
            try:
                client = self._get_client()
                system_msg = ""
                msg_list = []
                for m in messages:
                    if m["role"] == "system":
                        system_msg = m["content"]
                    else:
                        role = m["role"]
                        content = m.get("content") or ""
                        if role == "tool":
                            role = "user"
                            content = f"[Tool Result]\n{content}"
                        msg_list.append({"role": role, "content": content})
                kwargs: Dict[str, Any] = {"model": model, "messages": msg_list, "max_tokens": 8192}
                if system_msg:
                    kwargs["system"] = system_msg
                if tools:
                    kwargs["tools"] = self._convert_tools(tools)
                response = client.messages.create(**kwargs)
                self._breaker.record_success()
                result: Dict[str, Any] = {"role": "assistant", "content": "", "tool_calls": []}
                for block in response.content:
                    if block.type == "text":
                        result["content"] += block.text
                    elif block.type == "tool_use":
                        result["tool_calls"].append({
                            "id": block.id,
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input),
                            }
                        })
                return result
            except Exception as e:
                last_error = e
                self._breaker.record_failure()
                if attempt < self._retry._max_retries and self._retry.is_retryable(e):
                    if self._retry.is_rate_limit(e):
                        delay = self._retry.get_rate_limit_delay(e)
                    else:
                        delay = self._retry.get_delay(attempt)
                    time.sleep(delay)
                    continue
                raise

        raise last_error or Exception("All retries exhausted for anthropic")

    def chat_stream(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None) -> Generator[Dict[str, Any], None, None]:
        if not self._breaker.can_request():
            yield {"type": "error", "content": "Circuit breaker open for anthropic"}
            return

        last_error = None
        for attempt in range(self._retry._max_retries + 1):
            try:
                client = self._get_client()
                system_msg = ""
                msg_list = []
                for m in messages:
                    if m["role"] == "system":
                        system_msg = m["content"]
                    else:
                        role = m["role"]
                        content = m.get("content") or ""
                        if role == "tool":
                            role = "user"
                            content = f"[Tool Result]\n{content}"
                        msg_list.append({"role": role, "content": content})
                kwargs: Dict[str, Any] = {"model": model, "messages": msg_list, "max_tokens": 8192}
                if system_msg:
                    kwargs["system"] = system_msg
                if tools:
                    kwargs["tools"] = self._convert_tools(tools)
                with client.messages.stream(**kwargs) as stream:
                    current_tool_use = None
                    tool_input = ""
                    for event in stream:
                        if event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                yield {"type": "content", "content": event.delta.text}
                            elif event.delta.type == "input_json_delta":
                                tool_input += event.delta.partial_json
                        elif event.type == "content_block_start":
                            if event.content_block.type == "tool_use":
                                current_tool_use = {"id": event.content_block.id, "name": event.content_block.name}
                                tool_input = ""
                        elif event.type == "content_block_stop":
                            if current_tool_use:
                                yield {
                                    "type": "tool_calls",
                                    "tool_calls": [{
                                        "id": current_tool_use["id"],
                                        "function": {
                                            "name": current_tool_use["name"],
                                            "arguments": tool_input,
                                        }
                                    }]
                                }
                                current_tool_use = None
                                tool_input = ""
                self._breaker.record_success()
                return
            except Exception as e:
                last_error = e
                self._breaker.record_failure()
                if attempt < self._retry._max_retries and self._retry.is_retryable(e):
                    if self._retry.is_rate_limit(e):
                        delay = self._retry.get_rate_limit_delay(e)
                    else:
                        delay = self._retry.get_delay(attempt)
                    time.sleep(delay)
                    continue
                yield {"type": "error", "content": str(e)}
                return

        yield {"type": "error", "content": str(last_error)}

    def test_connection(self, model: str) -> Dict[str, Any]:
        try:
            result = self.chat([{"role": "user", "content": "Say hello in one word."}], model=model)
            return {"success": True, "response": result.get("content", "")[:100], "circuit_state": self._breaker.state}
        except Exception as e:
            return {"success": False, "error": str(e), "circuit_state": self._breaker.state}


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__("ollama", api_key="ollama", base_url="http://localhost:11434/v1")

    def chat(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None, stream: bool = False) -> Dict[str, Any]:
        provider = OpenAICompatibleProvider("ollama", api_key="ollama", base_url=self.base_url)
        return provider.chat(messages, model, tools, stream)

    def chat_stream(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None) -> Generator[Dict[str, Any], None, None]:
        provider = OpenAICompatibleProvider("ollama", api_key="ollama", base_url=self.base_url)
        yield from provider.chat_stream(messages, model, tools)

    def test_connection(self, model: str) -> Dict[str, Any]:
        try:
            import requests as req
            resp = req.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                return {"success": True, "response": "Ollama is running"}
            return {"success": False, "error": "Ollama not responding"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class BrowserAuthProvider(LLMProvider):
    def __init__(self, provider_id: str, token: str, base_url: Optional[str] = None) -> None:
        super().__init__(provider_id, api_key=token, base_url=base_url)
        self._token = token

    def chat(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None, stream: bool = False) -> Dict[str, Any]:
        if self.provider_id in ("openai", "deepseek"):
            provider = OpenAICompatibleProvider(self.provider_id, api_key=self._token, base_url=self.base_url)
            return provider.chat(messages, model, tools, stream)
        raise NotImplementedError(f"Browser auth not supported for {self.provider_id}")

    def chat_stream(self, messages: List[Dict], model: str, tools: Optional[List[Dict]] = None) -> Generator[Dict[str, Any], None, None]:
        if self.provider_id in ("openai", "deepseek"):
            provider = OpenAICompatibleProvider(self.provider_id, api_key=self._token, base_url=self.base_url)
            yield from provider.chat_stream(messages, model, tools)
        else:
            raise NotImplementedError(f"Browser auth not supported for {self.provider_id}")

    def test_connection(self, model: str) -> Dict[str, Any]:
        try:
            result = self.chat([{"role": "user", "content": "Say hello in one word."}], model=model)
            return {"success": True, "response": result.get("content", "")[:100]}
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_provider(provider_id: str, base_url: Optional[str] = None, use_browser_token: bool = False) -> LLMProvider:
    ks = get_keystore()
    if provider_id == "anthropic":
        key = ks.get_key("anthropic", "api_key")
        return AnthropicProvider(api_key=key, base_url=base_url)
    if provider_id == "ollama":
        return OllamaProvider()

    if use_browser_token:
        token = ks.get_key(provider_id, "browser_token")
        if token:
            from config import DEFAULT_PROVIDERS
            cfg = next((p for p in DEFAULT_PROVIDERS if p["id"] == provider_id), None)
            url = cfg["base_url"] if cfg else base_url
            return BrowserAuthProvider(provider_id, token, base_url=url)

    key = ks.get_key(provider_id, "api_key")
    from config import DEFAULT_PROVIDERS
    cfg = next((p for p in DEFAULT_PROVIDERS if p["id"] == provider_id), None)
    url = base_url or (cfg["base_url"] if cfg else None)
    return OpenAICompatibleProvider(provider_id, api_key=key, base_url=url)
