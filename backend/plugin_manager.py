from __future__ import annotations
import json
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class PluginManager:
    def __init__(self) -> None:
        self._plugins_dir = Path.home() / ".devin-clone" / "plugins"
        self._plugins_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_plugins: Dict[str, Dict[str, Any]] = {}
        self._custom_tools: Dict[str, Dict[str, Any]] = {}

    def list_plugins(self) -> Dict[str, Any]:
        plugins = []
        for f in self._plugins_dir.glob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(f.stem, str(f))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    info = getattr(mod, "PLUGIN_INFO", {})
                    plugins.append({
                        "name": info.get("name", f.stem),
                        "version": info.get("version", "0.0.1"),
                        "description": info.get("description", ""),
                        "author": info.get("author", ""),
                        "tools": info.get("tools", []),
                        "enabled": f.stem in self._loaded_plugins,
                        "file": str(f),
                    })
            except Exception as e:
                plugins.append({"name": f.stem, "error": str(e), "file": str(f)})
        return {"success": True, "plugins": plugins, "plugins_dir": str(self._plugins_dir)}

    def load_plugin(self, plugin_name: str) -> Dict[str, Any]:
        plugin_file = self._plugins_dir / f"{plugin_name}.py"
        if not plugin_file.exists():
            return {"success": False, "error": f"Plugin not found: {plugin_name}"}
        try:
            spec = importlib.util.spec_from_file_location(plugin_name, str(plugin_file))
            if not spec or not spec.loader:
                return {"success": False, "error": "Failed to load plugin spec"}
            mod = importlib.util.module_from_spec(spec)
            sys.modules[f"plugin_{plugin_name}"] = mod
            spec.loader.exec_module(mod)
            info = getattr(mod, "PLUGIN_INFO", {})
            tools = getattr(mod, "TOOLS", [])
            for tool in tools:
                tool_name = tool.get("name", "")
                if tool_name:
                    self._custom_tools[tool_name] = {
                        "schema": tool.get("schema", {}),
                        "handler": tool.get("handler"),
                        "plugin": plugin_name,
                    }
            self._loaded_plugins[plugin_name] = {"module": mod, "info": info, "tools": tools}
            return {"success": True, "message": f"Plugin {plugin_name} loaded", "tools_loaded": len(tools)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unload_plugin(self, plugin_name: str) -> Dict[str, Any]:
        if plugin_name in self._loaded_plugins:
            tools = self._loaded_plugins[plugin_name].get("tools", [])
            for tool in tools:
                tool_name = tool.get("name", "")
                self._custom_tools.pop(tool_name, None)
            del self._loaded_plugins[plugin_name]
            mod_name = f"plugin_{plugin_name}"
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            return {"success": True, "message": f"Plugin {plugin_name} unloaded"}
        return {"success": False, "error": "Plugin not loaded"}

    def install_plugin(self, source_code: str, name: str) -> Dict[str, Any]:
        try:
            plugin_file = self._plugins_dir / f"{name}.py"
            plugin_file.write_text(source_code, encoding="utf-8")
            return self.load_plugin(name)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def uninstall_plugin(self, plugin_name: str) -> Dict[str, Any]:
        self.unload_plugin(plugin_name)
        plugin_file = self._plugins_dir / f"{plugin_name}.py"
        if plugin_file.exists():
            plugin_file.unlink()
            return {"success": True, "message": f"Plugin {plugin_name} uninstalled"}
        return {"success": False, "error": "Plugin not found"}

    def get_custom_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = []
        for name, tool in self._custom_tools.items():
            schemas.append(tool["schema"])
        return schemas

    def dispatch_custom_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._custom_tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Custom tool not found: {tool_name}"}
        handler = tool.get("handler")
        if handler and callable(handler):
            try:
                return handler(args)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Tool handler not callable"}

    def create_plugin_template(self, name: str) -> Dict[str, Any]:
        template = f'''"""Plugin: {name}"""
PLUGIN_INFO = {{
    "name": "{name}",
    "version": "0.0.1",
    "description": "A custom plugin for Devin Clone",
    "author": "User",
    "tools": ["my_tool"],
}}

TOOLS = [
    {{
        "name": "my_tool",
        "description": "Description of what my_tool does",
        "schema": {{
            "type": "function",
            "function": {{
                "name": "my_tool",
                "description": "Description of what my_tool does",
                "parameters": {{
                    "type": "object",
                    "properties": {{
                        "input": {{"type": "string", "description": "Input parameter"}},
                    }},
                    "required": ["input"],
                }},
            }},
        }},
        "handler": my_tool_handler,
    }}
]


def my_tool_handler(args):
    """Implement your tool logic here."""
    input_val = args.get("input", "")
    return {{"success": True, "result": f"Processed: {{input_val}}"}}
'''
        try:
            plugin_file = self._plugins_dir / f"{name}.py"
            plugin_file.write_text(template, encoding="utf-8")
            return {"success": True, "path": str(plugin_file), "code": template}
        except Exception as e:
            return {"success": False, "error": str(e)}


class MCPServerManager:
    def __init__(self) -> None:
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._config_path = Path.home() / ".devin-clone" / "mcp_servers.json"
        self._load_config()

    def _load_config(self) -> None:
        if self._config_path.exists():
            try:
                self._servers = json.loads(self._config_path.read_text(encoding="utf-8"))
            except Exception:
                self._servers = {}

    def _save_config(self) -> None:
        self._config_path.write_text(json.dumps(self._servers, indent=2), encoding="utf-8")

    def add_server(self, name: str, command: str, args: List[str] = None, env: Dict[str, str] = None) -> Dict[str, Any]:
        self._servers[name] = {
            "command": command,
            "args": args or [],
            "env": env or {},
            "added_at": time.time(),
        }
        self._save_config()
        return {"success": True, "message": f"MCP server {name} added"}

    def remove_server(self, name: str) -> Dict[str, Any]:
        if name in self._servers:
            del self._servers[name]
            self._save_config()
            return {"success": True, "message": f"MCP server {name} removed"}
        return {"success": False, "error": "Server not found"}

    def list_servers(self) -> Dict[str, Any]:
        return {"success": True, "servers": self._servers}

    def get_server_tools(self, name: str) -> Dict[str, Any]:
        server = self._servers.get(name)
        if not server:
            return {"success": False, "error": "Server not found"}
        return {"success": True, "server": server, "tools": [], "message": "MCP server tools will be fetched when connected"}


_plugin_manager = PluginManager()
_mcp_manager = MCPServerManager()


def get_plugin_manager() -> PluginManager:
    return _plugin_manager


def get_mcp_manager() -> MCPServerManager:
    return _mcp_manager
