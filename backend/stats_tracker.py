from __future__ import annotations
import io
import json
import time
from typing import Any, Dict, List, Optional


class StatsTracker:
    def __init__(self) -> None:
        self._current_task: Optional[str] = None
        self._start_time: float = 0
        self._total_tokens: int = 0
        self._total_tool_calls: int = 0
        self._total_api_calls: int = 0
        self._total_cost: float = 0.0
        self._phase_times: List[Dict[str, Any]] = []
        self._current_phase: str = ""
        self._phase_start: float = 0
        self._history: List[Dict[str, Any]] = []

        self._cost_per_1k_tokens = {
            "openai": {"gpt-4o": 0.005, "gpt-4o-mini": 0.00015, "gpt-4-turbo": 0.01, "gpt-3.5-turbo": 0.0005},
            "anthropic": {"claude-sonnet-4-20250514": 0.003, "claude-3-5-sonnet-20241022": 0.003, "claude-3-5-haiku-20241022": 0.00025, "claude-3-opus-20240229": 0.015},
            "deepseek": {"deepseek-chat": 0.00014, "deepseek-reasoner": 0.00055},
            "groq": {"llama-3.3-70b-versatile": 0.0, "llama-3.1-8b-instant": 0.0, "gemma2-9b-it": 0.0, "mixtral-8x7b-32768": 0.0},
            "openrouter": {},
            "together": {},
            "ollama": {},
        }

    def start_task(self, task: str, provider: str, model: str) -> None:
        self._current_task = task
        self._start_time = time.time()
        self._total_tokens = 0
        self._total_tool_calls = 0
        self._total_api_calls = 0
        self._total_cost = 0.0
        self._phase_times = []
        self._current_phase = ""
        self._phase_start = time.time()

    def start_phase(self, phase: str) -> None:
        if self._current_phase and self._phase_start:
            elapsed = time.time() - self._phase_start
            self._phase_times.append({"phase": self._current_phase, "duration": elapsed})
        self._current_phase = phase
        self._phase_start = time.time()

    def end_phase(self) -> None:
        if self._current_phase and self._phase_start:
            elapsed = time.time() - self._phase_start
            self._phase_times.append({"phase": self._current_phase, "duration": elapsed})
            self._current_phase = ""
            self._phase_start = 0

    def record_api_call(self, provider: str, model: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self._total_api_calls += 1
        self._total_tokens += input_tokens + output_tokens
        cost_rates = self._cost_per_1k_tokens.get(provider, {}).get(model, 0)
        self._total_cost += ((input_tokens + output_tokens) / 1000) * cost_rates

    def record_tool_call(self) -> None:
        self._total_tool_calls += 1

    def get_current_stats(self) -> Dict[str, Any]:
        elapsed = time.time() - self._start_time if self._start_time else 0
        return {
            "task": self._current_task or "",
            "elapsed_seconds": round(elapsed, 1),
            "elapsed_formatted": self._format_time(elapsed),
            "total_tokens": self._total_tokens,
            "total_api_calls": self._total_api_calls,
            "total_tool_calls": self._total_tool_calls,
            "total_cost": round(self._total_cost, 4),
            "cost_formatted": f"${self._total_cost:.4f}" if self._total_cost > 0 else "Free",
            "current_phase": self._current_phase,
            "phase_times": self._phase_times,
        }

    def end_task(self) -> Dict[str, Any]:
        self.end_phase()
        stats = self.get_current_stats()
        self._history.append({
            "task": self._current_task,
            "stats": stats,
            "timestamp": time.time(),
        })
        return stats

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._history[-limit:]

    def get_dashboard_data(self) -> Dict[str, Any]:
        current = self.get_current_stats()
        history = self.get_history()
        total_tasks = len(history)
        total_time = sum(h["stats"]["elapsed_seconds"] for h in history)
        total_tokens_all = sum(h["stats"]["total_tokens"] for h in history)
        total_cost_all = sum(h["stats"]["total_cost"] for h in history)
        return {
            "current": current,
            "history": history,
            "totals": {
                "tasks_completed": total_tasks,
                "total_time_seconds": round(total_time, 1),
                "total_time_formatted": self._format_time(total_time),
                "total_tokens": total_tokens_all,
                "total_cost": round(total_cost_all, 4),
                "total_cost_formatted": f"${total_cost_all:.4f}",
            },
        }

    def _format_time(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = seconds % 60
        if minutes < 60:
            return f"{minutes}m {secs:.0f}s"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"


_stats = StatsTracker()


def get_stats() -> StatsTracker:
    return _stats
