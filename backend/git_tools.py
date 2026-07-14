from __future__ import annotations
import subprocess
import os
from typing import Any, Dict, List, Optional


class GitTools:
    def __init__(self) -> None:
        self._workspace_root: Optional[str] = None

    def set_workspace(self, path: str) -> None:
        self._workspace_root = path

    def _run(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        if not self._workspace_root:
            return {"success": False, "error": "No workspace connected"}
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self._workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except FileNotFoundError:
            return {"success": False, "error": "Git is not installed or not in PATH"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Git command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_git_repo(self) -> bool:
        result = self._run(["rev-parse", "--is-inside-work-tree"])
        return result.get("success", False)

    def init(self) -> Dict[str, Any]:
        return self._run(["init"])

    def status(self) -> Dict[str, Any]:
        result = self._run(["status", "--porcelain"])
        if not result.get("success"):
            return result
        lines = [l for l in result["stdout"].split("\n") if l.strip()]
        files = []
        for line in lines:
            status_code = line[:2].strip()
            filename = line[3:].strip()
            files.append({"status": status_code, "file": filename})
        return {"success": True, "files": files, "dirty": len(files) > 0}

    def log(self, count: int = 10) -> Dict[str, Any]:
        result = self._run(["log", f"--max-count={count}", "--pretty=format:%H|%an|%ae|%ai|%s"])
        if not result.get("success"):
            return result
        commits = []
        for line in result["stdout"].split("\n"):
            if "|" in line:
                parts = line.split("|", 4)
                if len(parts) == 5:
                    commits.append({
                        "hash": parts[0][:8],
                        "full_hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "date": parts[3],
                        "message": parts[4],
                    })
        return {"success": True, "commits": commits}

    def diff(self, file_path: Optional[str] = None, staged: bool = False) -> Dict[str, Any]:
        args = ["diff"]
        if staged:
            args.append("--cached")
        if file_path:
            args.append("--")
            args.append(file_path)
        result = self._run(args)
        return {"success": True, "diff": result.get("stdout", ""), "has_changes": bool(result.get("stdout", "").strip())}

    def diff_files(self) -> Dict[str, Any]:
        result = self._run(["diff", "--name-status"])
        if not result.get("success"):
            return result
        files = []
        for line in result["stdout"].split("\n"):
            if line.strip():
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    files.append({"status": parts[0], "file": parts[1]})
        return {"success": True, "files": files}

    def add(self, files: List[str]) -> Dict[str, Any]:
        return self._run(["add"] + files)

    def add_all(self) -> Dict[str, Any]:
        return self._run(["add", "-A"])

    def commit(self, message: str) -> Dict[str, Any]:
        return self._run(["commit", "-m", message])

    def commit_all(self, message: str) -> Dict[str, Any]:
        self.add_all()
        return self.commit(message)

    def branch_list(self) -> Dict[str, Any]:
        result = self._run(["branch", "-a"])
        if not result.get("success"):
            return result
        branches = []
        current = ""
        for line in result["stdout"].split("\n"):
            line = line.strip()
            if line.startswith("* "):
                current = line[2:]
                branches.append(current)
            elif line:
                branches.append(line)
        return {"success": True, "branches": branches, "current": current}

    def checkout(self, branch: str) -> Dict[str, Any]:
        return self._run(["checkout", branch])

    def create_branch(self, name: str) -> Dict[str, Any]:
        return self._run(["checkout", "-b", name])

    def push(self, remote: str = "origin", branch: str = "") -> Dict[str, Any]:
        if not branch:
            result = self._run(["branch", "--show-current"])
            branch = result.get("stdout", "main")
        return self._run(["push", remote, branch], timeout=60)

    def pull(self, remote: str = "origin", branch: str = "") -> Dict[str, Any]:
        if not branch:
            result = self._run(["branch", "--show-current"])
            branch = result.get("stdout", "main")
        return self._run(["pull", remote, branch], timeout=60)

    def stash(self) -> Dict[str, Any]:
        return self._run(["stash"])

    def stash_pop(self) -> Dict[str, Any]:
        return self._run(["stash", "pop"])

    def get_file_diff(self, file_path: str) -> Dict[str, Any]:
        result = self._run(["diff", "--", file_path])
        staged_result = self._run(["diff", "--cached", "--", file_path])
        return {
            "success": True,
            "unstaged": result.get("stdout", ""),
            "staged": staged_result.get("stdout", ""),
            "has_changes": bool(result.get("stdout", "").strip() or staged_result.get("stdout", "").strip()),
        }

    def auto_commit_phase(self, phase: str) -> Dict[str, Any]:
        status = self.status()
        if not status.get("success"):
            return status
        if not status.get("dirty"):
            return {"success": True, "message": "Nothing to commit"}
        self.add_all()
        return self.commit(f"[Devin Clone] {phase} phase completed")


_git_tools = GitTools()


def get_git_tools() -> GitTools:
    return _git_tools


GIT_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Check the git status of the workspace — see which files are modified, added, or deleted.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Show the diff of changes in the workspace. Optionally for a specific file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Optional: specific file to diff"},
                    "staged": {"type": "boolean", "description": "Show staged changes only"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stage all changes and commit with a message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Show recent git commit history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of commits to show (default: 10)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_branch",
            "description": "List branches or create a new branch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "create", "checkout"], "description": "Action to perform"},
                    "name": {"type": "string", "description": "Branch name (for create/checkout)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_push",
            "description": "Push committed changes to remote repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "remote": {"type": "string", "description": "Remote name (default: origin)"},
                },
            },
        },
    },
]


def dispatch_git_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    git = get_git_tools()
    if tool_name == "git_status":
        return git.status()
    elif tool_name == "git_diff":
        return git.diff(args.get("file_path"), args.get("staged", False))
    elif tool_name == "git_commit":
        return git.commit_all(args.get("message", "Auto commit by Devin Clone"))
    elif tool_name == "git_log":
        return git.log(args.get("count", 10))
    elif tool_name == "git_branch":
        action = args.get("action", "list")
        if action == "list":
            return git.branch_list()
        elif action == "create":
            return git.create_branch(args.get("name", "feature"))
        elif action == "checkout":
            return git.checkout(args.get("name", "main"))
    elif tool_name == "git_push":
        return git.push(args.get("remote", "origin"))
    return {"success": False, "error": f"Unknown git tool: {tool_name}"}
