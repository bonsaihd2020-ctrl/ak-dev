from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


class Workspace:
    def __init__(self) -> None:
        self._root: Optional[Path] = None
        self._connected: bool = False

    def connect(self, path: str) -> Dict[str, Any]:
        p = Path(path).resolve()
        if not p.exists():
            return {"success": False, "error": f"Path does not exist: {path}"}
        if p.is_file():
            self._root = p.parent
        else:
            self._root = p
        self._connected = True
        return {"success": True, "root": str(self._root), "is_file": p.is_file(), "connected_path": str(p)}

    def disconnect(self) -> None:
        self._root = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected and self._root is not None

    def get_root(self) -> Optional[Path]:
        return self._root

    def _guard(self, path: str) -> Path:
        if not self._connected or self._root is None:
            raise RuntimeError("No workspace connected")
        p = (self._root / path).resolve()
        if not str(p).startswith(str(self._root.resolve())):
            raise ValueError(f"Path traversal blocked: {path}")
        return p

    def read_file(self, path: str) -> Dict[str, Any]:
        try:
            p = self._guard(path)
            if not p.exists():
                return {"success": False, "error": f"File not found: {path}"}
            if not p.is_file():
                return {"success": False, "error": f"Not a file: {path}"}
            content = p.read_text(encoding="utf-8", errors="replace")
            return {"success": True, "content": content, "path": str(p.relative_to(self._root))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        try:
            p = self._guard(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(p.relative_to(self._root))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def edit_file(self, path: str, old_string: str, new_string: str) -> Dict[str, Any]:
        try:
            p = self._guard(path)
            if not p.exists():
                return {"success": False, "error": f"File not found: {path}"}
            content = p.read_text(encoding="utf-8", errors="replace")
            if old_string not in content:
                return {"success": False, "error": "old_string not found in file"}
            count = content.count(old_string)
            if count > 1:
                return {"success": False, "error": f"Found {count} matches. Provide more context."}
            new_content = content.replace(old_string, new_string, 1)
            p.write_text(new_content, encoding="utf-8")
            return {"success": True, "path": str(p.relative_to(self._root))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_dir(self, path: str = ".") -> Dict[str, Any]:
        try:
            p = self._guard(path)
            if not p.exists():
                return {"success": False, "error": f"Directory not found: {path}"}
            if not p.is_dir():
                return {"success": False, "error": f"Not a directory: {path}"}
            entries = []
            for item in sorted(p.iterdir()):
                rel = str(item.relative_to(self._root))
                entries.append({
                    "name": item.name,
                    "path": rel,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            return {"success": True, "entries": entries, "path": str(p.relative_to(self._root))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_file_tree(self, max_depth: int = 4) -> Dict[str, Any]:
        if not self.is_connected():
            return {"success": False, "error": "No workspace connected"}
        tree = self._build_tree(self._root, self._root, max_depth, 0)
        return {"success": True, "tree": tree}

    def _build_tree(self, root: Path, current: Path, max_depth: int, depth: int) -> Dict[str, Any]:
        node: Dict[str, Any] = {"name": current.name or str(root), "path": str(current.relative_to(root)), "is_dir": current.is_dir()}
        if current.is_dir() and depth < max_depth:
            children = []
            try:
                for item in sorted(current.iterdir()):
                    if item.name.startswith(".") and item.name not in (".gitignore", ".env.example"):
                        continue
                    if item.name == "node_modules" or item.name == "__pycache__":
                        continue
                    children.append(self._build_tree(root, item, max_depth, depth + 1))
            except PermissionError:
                pass
            node["children"] = children
        return node

    def get_sync_dir(self) -> Optional[Path]:
        return self._root

    def list_files_recursive(self) -> List[str]:
        if not self.is_connected():
            return []
        files = []
        for item in self._root.rglob("*"):
            if item.is_file():
                rel = str(item.relative_to(self._root))
                if "node_modules" in rel or "__pycache__" in rel or ".git" in rel:
                    continue
                files.append(rel)
        return files


_workspace = Workspace()


def get_workspace() -> Workspace:
    return _workspace
