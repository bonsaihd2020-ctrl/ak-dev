from __future__ import annotations
import asyncio
import json
import time
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from config import MAX_AGENT_ITERATIONS, AGENT_RETRY_BUDGET
from memory import get_memory
from tools import ALL_TOOL_SCHEMAS, dispatch_tool


class AgentLoop:
    def __init__(self, provider, model: str, system_prompt: str, memory: Optional[Any] = None) -> None:
        self.provider = provider
        self.model = model
        self.system_prompt = system_prompt
        self.memory = memory or get_memory()
        self.max_iterations = MAX_AGENT_ITERATIONS
        self.retry_budget = AGENT_RETRY_BUDGET
        self._paused = False
        self._stopped = False
        self._on_step: Optional[Callable] = None

    def set_on_step(self, callback: Callable) -> None:
        self._on_step = callback

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._stopped = True

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        if self._on_step:
            self._on_step({"type": event_type, **data})

    async def run(self, task: str, context: Optional[Dict] = None) -> AsyncGenerator[Dict[str, Any], None]:
        self._paused = False
        self._stopped = False
        self.memory.clear()
        self.memory.add_message("user", task, agent="user")

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]
        if context:
            context_msg = f"Additional context:\n{json.dumps(context, indent=2)}"
            messages.append({"role": "user", "content": context_msg})

        iteration = 0
        consecutive_errors = 0

        while iteration < self.max_iterations and not self._stopped:
            while self._paused:
                await asyncio.sleep(0.5)
                if self._stopped:
                    break

            iteration += 1
            self._emit("iteration", {"iteration": iteration, "max": self.max_iterations})

            try:
                if iteration > 3 and iteration % 5 == 0:
                    compressed = self.memory.get_compressed_messages(self.system_prompt, self.provider, self.model)
                    if len(compressed) < len(messages):
                        messages = compressed
                        self._emit("context_compressed", {"new_length": len(messages)})

                full_response = {"role": "assistant", "content": "", "tool_calls": []}
                content_parts = []

                for chunk in self.provider.chat_stream(messages, self.model, tools=ALL_TOOL_SCHEMAS):
                    if self._stopped:
                        break
                    if chunk["type"] == "content":
                        content_parts.append(chunk["content"])
                        self._emit("content", {"content": chunk["content"]})
                    elif chunk["type"] == "tool_calls":
                        full_response["tool_calls"] = chunk["tool_calls"]

                full_response["content"] = "".join(content_parts)
                messages.append(full_response)
                self.memory.add_message("assistant", full_response["content"], agent="current")
                consecutive_errors = 0

                if not full_response["tool_calls"]:
                    self._emit("done", {"content": full_response["content"]})
                    yield {"event": "done", "content": full_response["content"], "iterations": iteration}
                    return

                for tc in full_response["tool_calls"]:
                    func_name = tc["function"]["name"]
                    try:
                        func_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        func_args = {}

                    self._emit("tool_call", {"tool": func_name, "args": func_args})
                    result = dispatch_tool(func_name, func_args)
                    self.memory.record_tool_call(func_name, func_args, result)

                    if not result.get("success", True):
                        consecutive_errors += 1
                        if consecutive_errors >= self.retry_budget:
                            error_msg = f"Too many consecutive errors ({consecutive_errors}). Last error: {result.get('error', 'unknown')}"
                            self._emit("error", {"message": error_msg})
                            messages.append({"role": "user", "content": f"Error: {result.get('error')}. Please try a different approach."})
                            consecutive_errors = 0
                            continue
                        result_content = f"ERROR: {result.get('error', 'Unknown error')}\nPlease fix this and try again."
                    else:
                        result_content = json.dumps(result, indent=2)

                    if func_name in ("write_file", "edit_file") and result.get("success"):
                        self.memory.track_file_change(func_args.get("path", ""), created=(func_name == "write_file"))

                    self._emit("tool_result", {"tool": func_name, "result": result})
                    messages.append({
                        "role": "tool",
                        "content": result_content,
                    })

                self.memory.trim_context()

            except Exception as e:
                consecutive_errors += 1
                self._emit("error", {"message": str(e)})
                messages.append({"role": "user", "content": f"Error occurred: {str(e)}. Please continue from where you left off."})
                if consecutive_errors >= self.retry_budget:
                    self._emit("done", {"content": f"Agent stopped due to repeated errors: {str(e)}"})
                    yield {"event": "done", "content": f"Agent stopped due to repeated errors: {str(e)}", "iterations": iteration}
                    return

        self._emit("done", {"content": "Reached maximum iterations limit."})
        yield {"event": "done", "content": "Reached maximum iterations limit.", "iterations": iteration}
