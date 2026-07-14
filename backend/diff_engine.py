from __future__ import annotations
import difflib
from typing import Any, Dict, List, Optional


def compute_diff(old_content: str, new_content: str, old_label: str = "before", new_label: str = "after") -> Dict[str, Any]:
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=old_label, tofile=new_label, lineterm=""))

    changes = []
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("@@"):
            changes.append({"type": "header", "content": line.strip()})
        elif line.startswith("+"):
            changes.append({"type": "add", "content": line[1:]})
        elif line.startswith("-"):
            changes.append({"type": "remove", "content": line[1:]})
        else:
            changes.append({"type": "context", "content": line[1:] if line.startswith(" ") else line})

    return {
        "success": True,
        "diff_text": "".join(diff),
        "changes": changes,
        "additions": sum(1 for c in changes if c["type"] == "add"),
        "deletions": sum(1 for c in changes if c["type"] == "remove"),
        "has_changes": len(changes) > 0,
    }


def compute_file_diff(file_path: str, old_content: str, new_content: str) -> Dict[str, Any]:
    return compute_diff(old_content, new_content, old_label=f"a/{file_path}", new_label=f"b/{file_path}")


def compute_side_by_side(file_path: str, old_content: str, new_content: str) -> Dict[str, Any]:
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    sm = difflib.SequenceMatcher(None, old_lines, new_lines)
    side_by_side = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for i in range(i1, i2):
                side_by_side.append({
                    "type": "equal",
                    "old_num": i + 1,
                    "new_num": i + 1,
                    "old_line": old_lines[i],
                    "new_line": new_lines[i] if j1 + (i - i1) < j2 else "",
                })
        elif tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                old_num = i1 + k + 1 if i1 + k < i2 else ""
                new_num = j1 + k + 1 if j1 + k < j2 else ""
                old_line = old_lines[i1 + k] if i1 + k < i2 else ""
                new_line = new_lines[j1 + k] if j1 + k < j2 else ""
                side_by_side.append({
                    "type": "replace",
                    "old_num": old_num,
                    "new_num": new_num,
                    "old_line": old_line,
                    "new_line": new_line,
                })
        elif tag == "delete":
            for i in range(i1, i2):
                side_by_side.append({
                    "type": "delete",
                    "old_num": i + 1,
                    "new_num": "",
                    "old_line": old_lines[i],
                    "new_line": "",
                })
        elif tag == "insert":
            for j in range(j1, j2):
                side_by_side.append({
                    "type": "insert",
                    "old_num": "",
                    "new_num": j + 1,
                    "old_line": "",
                    "new_line": new_lines[j],
                })

    return {
        "success": True,
        "file": file_path,
        "side_by_side": side_by_side,
        "total_old_lines": len(old_lines),
        "total_new_lines": len(new_lines),
    }


def get_diff_stats(diffs: List[Dict]) -> Dict[str, Any]:
    total_additions = 0
    total_deletions = 0
    files_changed = []
    for d in diffs:
        total_additions += d.get("additions", 0)
        total_deletions += d.get("deletions", 0)
        files_changed.append(d.get("file", ""))
    return {
        "files_changed": len(files_changed),
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "files": files_changed,
    }
