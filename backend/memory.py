from __future__ import annotations
import json
import time
import threading
from typing import Any, Dict, List, Optional


class ContextSummary:
    def __init__(self, content: str, message_range: tuple, timestamp: float) -> None:
        self.content = content
        self.message_range = message_range
        self.timestamp = timestamp
        self.id = f"summary_{int(timestamp * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "start_idx": self.message_range[0],
            "end_idx": self.message_range[1],
            "timestamp": self.timestamp,
        }


class ExperienceEntry:
    def __init__(self, task: str, outcome: str, tools_used: List[str], success: bool) -> None:
        self.task = task
        self.outcome = outcome
        self.tools_used = tools_used
        self.success = success
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "outcome": self.outcome,
            "tools_used": self.tools_used,
            "success": self.success,
            "timestamp": self.timestamp,
        }


class Memory:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.conversation: List[Dict[str, Any]] = []
        self.steps_completed: List[Dict[str, Any]] = []
        self.files_modified: List[str] = []
        self.files_created: List[str] = []
        self.tool_calls_log: List[Dict[str, Any]] = []
        self.context_tokens_estimate: int = 0
        self._max_context_tokens: int = 100000
        self.summaries: List[ContextSummary] = []
        self.summarized_message_ids: set = set()
        self.experience_pool: List[ExperienceEntry] = []
        self.collected_keywords: List[str] = []
        self.current_plan: Optional[Dict[str, Any]] = None
        self.agent_monologue: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str, agent: str = "", extra: Optional[Dict] = None) -> Dict[str, Any]:
        with self._lock:
            msg_id = f"msg_{len(self.conversation)}_{int(time.time() * 1000)}"
            msg: Dict[str, Any] = {"id": msg_id, "role": role, "content": content, "timestamp": time.time()}
            if agent:
                msg["agent"] = agent
            if extra:
                msg.update(extra)
            self.conversation.append(msg)
            self.context_tokens_estimate += len(content) // 4
            self._extract_keywords(content)
            return msg

    def get_messages_for_llm(self, system_prompt: str, max_messages: int = 50) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt}]
        recent = self.conversation[-max_messages:]
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant", "tool"):
                messages.append({"role": role, "content": content})
        return messages

    def get_compressed_messages(self, system_prompt: str, provider=None, model: str = "") -> List[Dict[str, str]]:
        if not provider:
            return self.get_messages_for_llm(system_prompt)

        total_tokens = self._estimate_total_tokens()
        context_limit = self._max_context_tokens

        if total_tokens < context_limit * 0.7:
            return self.get_messages_for_llm(system_prompt)

        summary_text = self._summarize_old_messages(provider, model)
        if not summary_text:
            return self.get_messages_for_llm(system_prompt)

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({
            "role": "user",
            "content": f"[CONTEXT SUMMARY]\n{summary_text}\n[/CONTEXT SUMMARY]\n\nContinue from where the summary ends."
        })

        recent = self.conversation[-15:]
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant", "tool") and content:
                messages.append({"role": role, "content": content})

        return messages

    def _summarize_old_messages(self, provider, model: str) -> str:
        if len(self.conversation) < 10:
            return ""

        old_messages = self.conversation[:-10]
        old_text = "\n".join([
            f"[{m.get('role', 'unknown')}]: {m.get('content', '')[:200]}"
            for m in old_messages if m.get("content")
        ])

        if not old_text.strip():
            return ""

        summary_prompt = (
            "Summarize the following conversation into a concise context summary. "
            "Focus on: what was discussed, key decisions, files created/modified, "
            "errors encountered, and current state. Keep it under 500 words.\n\n"
            f"Conversation:\n{old_text[:3000]}"
        )

        try:
            result = provider.chat(
                [{"role": "user", "content": summary_prompt}],
                model=model,
                stream=False,
            )
            summary = result.get("content", "")
            if summary:
                ctx_summary = ContextSummary(
                    content=summary,
                    message_range=(0, len(old_messages)),
                    timestamp=time.time(),
                )
                self.summaries.append(ctx_summary)
                return summary
        except Exception:
            pass
        return ""

    def _estimate_total_tokens(self) -> int:
        return sum(len(m.get("content", "")) // 4 for m in self.conversation)

    def _extract_keywords(self, text: str) -> None:
        if not text or len(text) < 10:
            return
        words = text.lower().split()
        important = [w for w in words if len(w) > 4 and w.isalpha()]
        seen = set(self.collected_keywords)
        for word in important[:3]:
            if word not in seen and len(self.collected_keywords) < 100:
                self.collected_keywords.append(word)

    def add_monologue(self, agent: str, thought: str) -> None:
        with self._lock:
            self.agent_monologue.append({
                "agent": agent,
                "thought": thought,
                "timestamp": time.time(),
            })

    def get_recent_monologue(self, count: int = 5) -> List[Dict[str, Any]]:
        return self.agent_monologue[-count:]

    def set_plan(self, plan: Dict[str, Any]) -> None:
        self.current_plan = plan

    def get_plan(self) -> Optional[Dict[str, Any]]:
        return self.current_plan

    def add_experience(self, task: str, outcome: str, tools_used: List[str], success: bool) -> None:
        with self._lock:
            entry = ExperienceEntry(task, outcome, tools_used, success)
            self.experience_pool.append(entry)
            if len(self.experience_pool) > 50:
                self.experience_pool = self.experience_pool[-50:]

    def get_relevant_experiences(self, task: str, limit: int = 3) -> List[Dict[str, Any]]:
        task_words = set(task.lower().split())
        scored = []
        for exp in self.experience_pool:
            exp_words = set(exp.task.lower().split())
            overlap = len(task_words & exp_words)
            scored.append((overlap, exp))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1].to_dict() for s in scored[:limit] if s[0] > 0]

    def record_tool_call(self, tool_name: str, args: Dict, result: Dict) -> None:
        with self._lock:
            self.tool_calls_log.append({
                "tool": tool_name,
                "args": args,
                "result": result,
                "timestamp": time.time(),
            })

    def record_step(self, agent: str, description: str, status: str = "completed") -> None:
        with self._lock:
            self.steps_completed.append({
                "agent": agent,
                "description": description,
                "status": status,
                "timestamp": time.time(),
            })

    def track_file_change(self, path: str, created: bool = False) -> None:
        with self._lock:
            if created and path not in self.files_created:
                self.files_created.append(path)
            if path not in self.files_modified:
                self.files_modified.append(path)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_messages": len(self.conversation),
            "steps_completed": len(self.steps_completed),
            "tool_calls": len(self.tool_calls_log),
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "context_tokens_estimate": self.context_tokens_estimate,
            "summaries_count": len(self.summaries),
            "experiences_count": len(self.experience_pool),
            "keywords_collected": len(self.collected_keywords),
        }

    def trim_context(self, keep_recent: int = 30) -> None:
        if len(self.conversation) > keep_recent + 10:
            trimmed = self.conversation[:5] + self.conversation[-keep_recent:]
            self.conversation = trimmed
            self.context_tokens_estimate = sum(len(m.get("content", "")) for m in self.conversation) // 4

    def clear(self) -> None:
        with self._lock:
            self.conversation.clear()
            self.steps_completed.clear()
            self.files_modified.clear()
            self.files_created.clear()
            self.tool_calls_log.clear()
            self.context_tokens_estimate = 0
            self.summaries.clear()
            self.summarized_message_ids.clear()
            self.agent_monologue.clear()
            self.current_plan = None
            self.collected_keywords.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation": self.conversation,
            "steps_completed": self.steps_completed,
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "tool_calls_log": self.tool_calls_log,
            "summaries": [s.to_dict() for s in self.summaries],
            "experience_pool": [e.to_dict() for e in self.experience_pool],
            "agent_monologue": self.agent_monologue,
        }


_memory = Memory()


def get_memory() -> Memory:
    return _memory
