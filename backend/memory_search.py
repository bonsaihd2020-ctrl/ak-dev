from __future__ import annotations
import json
import os
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher


class MemorySearch:
    def __init__(self) -> None:
        self._index_dir = Path.home() / ".devin-clone" / "memory_index"
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._conversations_dir = self._index_dir / "conversations"
        self._conversations_dir.mkdir(exist_ok=True)

    def index_conversation(self, session_id: str, task: str, conversation: List[Dict], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            entry = {
                "session_id": session_id,
                "task": task,
                "task_lower": task.lower(),
                "messages": conversation,
                "metadata": metadata or {},
                "indexed_at": time.time(),
                "keywords": self._extract_keywords(task),
            }
            path = self._conversations_dir / f"{session_id}.json"
            path.write_text(json.dumps(entry, indent=2, default=str), encoding="utf-8")
            return {"success": True, "session_id": session_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        query_lower = query.lower()
        query_words = set(query_lower.split())
        results = []

        for f in self._conversations_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                score = self._score_result(data, query_lower, query_words)
                if score > 0.1:
                    results.append({
                        "session_id": data.get("session_id", f.stem),
                        "task": data.get("task", ""),
                        "score": round(score, 3),
                        "message_count": len(data.get("messages", [])),
                        "indexed_at": data.get("indexed_at", 0),
                        "metadata": data.get("metadata", {}),
                    })
            except Exception:
                continue

        results.sort(key=lambda x: x["score"], reverse=True)
        return {"success": True, "results": results[:limit], "total": len(results)}

    def get_conversation(self, session_id: str) -> Dict[str, Any]:
        try:
            path = self._conversations_dir / f"{session_id}.json"
            if not path.exists():
                return {"success": False, "error": "Conversation not found"}
            data = json.loads(path.read_text(encoding="utf-8"))
            return {"success": True, "conversation": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_recent(self, limit: int = 10) -> Dict[str, Any]:
        entries = []
        for f in self._conversations_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                entries.append({
                    "session_id": data.get("session_id", f.stem),
                    "task": data.get("task", ""),
                    "indexed_at": data.get("indexed_at", 0),
                })
            except Exception:
                continue
        entries.sort(key=lambda x: x["indexed_at"], reverse=True)
        return {"success": True, "entries": entries[:limit]}

    def delete(self, session_id: str) -> Dict[str, Any]:
        try:
            path = self._conversations_dir / f"{session_id}.json"
            if path.exists():
                path.unlink()
                return {"success": True}
            return {"success": False, "error": "Not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _score_result(self, data: Dict, query_lower: str, query_words: set) -> float:
        score = 0.0
        task = data.get("task_lower", "")
        task_words = set(task.split())

        overlap = query_words.intersection(task_words)
        if overlap:
            score += len(overlap) / max(len(query_words), 1) * 0.5

        sm = SequenceMatcher(None, query_lower, task)
        ratio = sm.ratio()
        score += ratio * 0.3

        keywords = set(data.get("keywords", []))
        keyword_overlap = query_words.intersection(keywords)
        if keyword_overlap:
            score += len(keyword_overlap) / max(len(query_words), 1) * 0.2

        messages = data.get("messages", [])
        for msg in messages[-20:]:
            content = msg.get("content", "").lower()
            for word in query_words:
                if word in content:
                    score += 0.05
                    break

        return min(score, 1.0)

    def _extract_keywords(self, text: str) -> List[str]:
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                       "have", "has", "had", "do", "does", "did", "will", "would", "could",
                       "should", "may", "might", "shall", "can", "need", "dare", "ought",
                       "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
                       "as", "into", "through", "during", "before", "after", "above", "below",
                       "between", "out", "off", "over", "under", "again", "further", "then",
                       "once", "and", "but", "or", "nor", "not", "so", "very", "just",
                       "that", "this", "these", "those", "i", "me", "my", "we", "our",
                       "you", "your", "he", "him", "his", "she", "her", "it", "its",
                       "they", "them", "their", "what", "which", "who", "whom"}
        words = text.lower().split()
        return [w for w in words if len(w) > 2 and w.isalnum() and w not in stop_words]


_memory_search = MemorySearch()


def get_memory_search() -> MemorySearch:
    return _memory_search
