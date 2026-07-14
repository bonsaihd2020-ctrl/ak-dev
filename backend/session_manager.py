from __future__ import annotations
import json
import os
import time
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


class SessionManager:
    def __init__(self) -> None:
        self._sessions_dir = Path.home() / ".devin-clone" / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_file(self, session_id: str) -> Path:
        return self._sessions_dir / f"{session_id}.json"

    def save_session(
        self,
        session_id: str,
        task: str,
        provider: str,
        model: str,
        workspace_path: str,
        conversation: List[Dict],
        steps: List[Dict],
        files_created: List[str],
        files_modified: List[str],
        tool_calls: List[Dict],
        summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        session_data = {
            "id": session_id,
            "task": task,
            "provider": provider,
            "model": model,
            "workspace_path": workspace_path,
            "conversation": conversation,
            "steps": steps,
            "files_created": files_created,
            "files_modified": files_modified,
            "tool_calls": tool_calls,
            "summary": summary,
            "created_at": time.time(),
            "updated_at": time.time(),
            "status": "saved",
        }
        try:
            path = self._get_session_file(session_id)
            path.write_text(json.dumps(session_data, indent=2, default=str), encoding="utf-8")
            return {"success": True, "session_id": session_id, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_session(self, session_id: str) -> Dict[str, Any]:
        try:
            path = self._get_session_file(session_id)
            if not path.exists():
                return {"success": False, "error": f"Session not found: {session_id}"}
            data = json.loads(path.read_text(encoding="utf-8"))
            return {"success": True, "session": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_sessions(self, limit: int = 50) -> Dict[str, Any]:
        sessions = []
        for f in sorted(self._sessions_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                sessions.append({
                    "id": data.get("id", f.stem),
                    "task": data.get("task", "")[:100],
                    "provider": data.get("provider", ""),
                    "model": data.get("model", ""),
                    "status": data.get("status", "unknown"),
                    "created_at": data.get("created_at", 0),
                    "updated_at": data.get("updated_at", 0),
                    "files_created": len(data.get("files_created", [])),
                    "files_modified": len(data.get("files_modified", [])),
                    "total_messages": len(data.get("conversation", [])),
                })
            except Exception:
                continue
            if len(sessions) >= limit:
                break
        return {"success": True, "sessions": sessions, "total": len(sessions)}

    def delete_session(self, session_id: str) -> Dict[str, Any]:
        try:
            path = self._get_session_file(session_id)
            if path.exists():
                path.unlink()
                return {"success": True, "message": f"Session {session_id} deleted"}
            return {"success": False, "error": "Session not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        try:
            path = self._get_session_file(session_id)
            if not path.exists():
                return {"success": False, "error": "Session not found"}
            data = json.loads(path.read_text(encoding="utf-8"))
            data.update(updates)
            data["updated_at"] = time.time()
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_session_id(self, task: str) -> str:
        import hashlib
        timestamp = str(int(time.time()))
        task_hash = hashlib.md5(f"{task}{timestamp}".encode()).hexdigest()[:8]
        return f"session_{task_hash}_{timestamp}"


_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    return _session_manager
