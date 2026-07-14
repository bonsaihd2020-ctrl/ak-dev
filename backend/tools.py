from __future__ import annotations
import json
from typing import Any, Callable, Dict, List, Optional

from workspace import get_workspace
from sandbox_manager import get_sandbox
from git_tools import GIT_TOOL_SCHEMAS, dispatch_git_tool


def read_file(args: Dict[str, Any]) -> Dict[str, Any]:
    ws = get_workspace()
    return ws.read_file(args["path"])


def write_file(args: Dict[str, Any]) -> Dict[str, Any]:
    ws = get_workspace()
    return ws.write_file(args["path"], args["content"])


def edit_file(args: Dict[str, Any]) -> Dict[str, Any]:
    ws = get_workspace()
    return ws.edit_file(args["path"], args["old_string"], args["new_string"])


def list_dir(args: Dict[str, Any]) -> Dict[str, Any]:
    ws = get_workspace()
    return ws.list_dir(args.get("path", "."))


def run_in_sandbox(args: Dict[str, Any]) -> Dict[str, Any]:
    sandbox = get_sandbox()
    if not sandbox.is_running():
        start_result = sandbox.start()
        if not start_result.get("success"):
            return {"success": False, "error": f"Failed to start sandbox: {start_result.get('error')}"}
    ws = get_workspace()
    if ws.is_connected():
        sync_result = sandbox.sync_workspace(ws.get_sync_dir())
    return sandbox.exec_command(args["command"], timeout=args.get("timeout", 60))


def install_browser_extension(args: Dict[str, Any]) -> Dict[str, Any]:
    sandbox = get_sandbox()
    if not sandbox.is_running():
        start_result = sandbox.start()
        if not start_result.get("success"):
            return {"success": False, "error": f"Failed to start sandbox: {start_result.get('error')}"}
    ext_url = args.get("extension_url", "")
    cmd = f"chromium --no-sandbox --install-extension={ext_url}" if ext_url else "echo 'No extension URL provided'"
    return sandbox.exec_command(cmd, timeout=120)


def browser_action(args: Dict[str, Any]) -> Dict[str, Any]:
    sandbox = get_sandbox()
    if not sandbox.is_running():
        return {"success": False, "error": "Sandbox not running. Start it first."}
    url = args.get("url", "https://google.com")
    action = args.get("action", "navigate")
    if action == "navigate":
        return sandbox.exec_command(f"chromium --no-sandbox '{url}' &", timeout=10)
    return {"success": False, "error": f"Unknown browser action: {action}"}


def web_search(args: Dict[str, Any]) -> Dict[str, Any]:
    from keystore import get_keystore
    ks = get_keystore()
    query = args.get("query", "")
    backend = args.get("backend", "tavily")
    if backend == "tavily":
        key = ks.get_search_key("tavily")
        if not key:
            return {"success": False, "error": "No Tavily API key configured. Add it in Settings."}
        try:
            import requests
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": key, "query": query, "max_results": args.get("max_results", 5)},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                formatted = [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")} for r in results]
                return {"success": True, "results": formatted, "answer": data.get("answer", "")}
            return {"success": False, "error": f"Tavily error: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    elif backend == "brave":
        key = ks.get_search_key("brave")
        if not key:
            return {"success": False, "error": "No Brave API key configured. Add it in Settings."}
        try:
            import requests
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": key, "Accept": "application/json"},
                params={"q": query, "count": args.get("max_results", 5)},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("web", {}).get("results", [])
                formatted = [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("description", "")} for r in results]
                return {"success": True, "results": formatted}
            return {"success": False, "error": f"Brave error: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": f"Unknown search backend: {backend}"}


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the connected workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the connected workspace. Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"},
                    "content": {"type": "string", "description": "Full content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific string in a file with a new string. The old_string must be unique in the file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"},
                    "old_string": {"type": "string", "description": "The exact string to replace"},
                    "new_string": {"type": "string", "description": "The replacement string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List contents of a directory in the connected workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the directory (default: root)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_in_sandbox",
            "description": "Execute a shell command inside the Ubuntu sandbox container. Use this for running/testing code, installing packages, etc. The sandbox is started automatically if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_browser_extension",
            "description": "Install a Chrome/Chromium extension inside the sandbox browser. Requires sandbox to be running.",
            "parameters": {
                "type": "object",
                "properties": {
                    "extension_url": {"type": "string", "description": "URL or ID of the Chrome extension to install"},
                },
                "required": ["extension_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_action",
            "description": "Perform an action in the sandbox browser (navigate to URL, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"},
                    "action": {"type": "string", "description": "Action to perform (navigate, click, etc)", "enum": ["navigate", "screenshot"]},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using Tavily or Brave Search API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "backend": {"type": "string", "description": "Search backend to use", "enum": ["tavily", "brave"]},
                    "max_results": {"type": "integer", "description": "Maximum results to return (default: 5)"},
                },
                "required": ["query"],
            },
        },
    },
]

TOOL_DISPATCH: Dict[str, Callable] = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_dir": list_dir,
    "run_in_sandbox": run_in_sandbox,
    "install_browser_extension": install_browser_extension,
    "browser_action": browser_action,
    "web_search": web_search,
}

ALL_TOOL_SCHEMAS = TOOL_SCHEMAS + GIT_TOOL_SCHEMAS


def dispatch_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name.startswith("git_"):
        return dispatch_git_tool(tool_name, args)
    fn = TOOL_DISPATCH.get(tool_name)
    if fn is None:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    try:
        return fn(args)
    except Exception as e:
        return {"success": False, "error": str(e)}
