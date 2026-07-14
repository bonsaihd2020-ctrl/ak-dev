from __future__ import annotations
import asyncio
import io
import json
import os
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field

from config import API_HOST, API_PORT, DEFAULT_PROVIDERS, SEARCH_BACKENDS
from keystore import get_keystore
from providers import get_provider, OpenAICompatibleProvider, AnthropicProvider, OllamaProvider
from models_catalog import get_models_for_provider, get_all_providers_with_models
from api_check import test_provider_key, test_tavily_key, test_brave_key
from workspace import get_workspace
from sandbox_manager import get_sandbox
from memory import get_memory
from agents.orchestrator import Orchestrator
from browser_auth import get_browser_auth
from session_manager import get_session_manager
from stats_tracker import get_stats
from git_tools import get_git_tools
from diff_engine import compute_diff, compute_side_by_side
from memory_search import get_memory_search
from auto_update import get_update_checker
from plugin_manager import get_plugin_manager, get_mcp_manager
from template_manager import get_template_manager
from docker_compose import get_compose_manager

app = FastAPI(title="Devin Clone Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_limit_store: Dict[str, List[float]] = {}
_RATE_LIMIT_WINDOW = 60.0
_RATE_LIMIT_MAX = 30


def _check_rate_limit(client_id: str = "default") -> bool:
    now = time.time()
    if client_id not in _rate_limit_store:
        _rate_limit_store[client_id] = []
    _rate_limit_store[client_id] = [t for t in _rate_limit_store[client_id] if now - t < _RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[client_id]) >= _RATE_LIMIT_MAX:
        return False
    _rate_limit_store[client_id].append(now)
    return True


class RunRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=50000)
    provider: str = Field(default="openai", pattern=r"^[a-z0-9_-]+$")
    model: str = Field(default="gpt-4o", pattern=r"^[a-zA-Z0-9._/-]+$")
    use_browser_token: bool = False
    context: Optional[Dict[str, Any]] = None


class ControlRequest(BaseModel):
    action: str  # pause, resume, stop


class KeyRequest(BaseModel):
    provider_id: str
    key: str
    key_type: str = "api_key"


class SearchKeyRequest(BaseModel):
    backend: str
    key: str


class WorkspaceConnectRequest(BaseModel):
    path: str


class ApiCheckRequest(BaseModel):
    provider_id: str
    model: str
    base_url: Optional[str] = None
    use_browser_token: bool = False


class ModelSelectionRequest(BaseModel):
    provider_id: str
    model: str


class BrowserLoginRequest(BaseModel):
    provider_id: str


class ManualTokenRequest(BaseModel):
    provider_id: str
    token: str


class OAuthCallbackRequest(BaseModel):
    provider_id: str
    code: str
    state: str


class SearchBackendRequest(BaseModel):
    backend: str


class SessionSaveRequest(BaseModel):
    session_id: str
    task: str
    provider: str
    model: str


class DiffRequest(BaseModel):
    old_content: str
    new_content: str
    file_path: str = "file"


class GitInitRequest(BaseModel):
    pass


class GitCommitRequest(BaseModel):
    message: str


class GitBranchRequest(BaseModel):
    action: str
    name: str = ""


class SearchMemoryRequest(BaseModel):
    query: str
    limit: int = 10


class PluginInstallRequest(BaseModel):
    name: str
    source_code: str


class PluginTemplateRequest(BaseModel):
    name: str


class TemplateCreateRequest(BaseModel):
    template_id: str
    target_dir: str
    project_name: str = ""


class ComposeUpRequest(BaseModel):
    build: bool = True


class ComposeGenerateRequest(BaseModel):
    services: List[Dict[str, Any]]


class MCPServerRequest(BaseModel):
    name: str
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}


_orchestrator: Optional[Orchestrator] = None


@app.get("/")
async def root():
    return {"status": "running", "app": "Devin Clone", "version": "1.0.0"}


@app.get("/providers")
async def list_providers():
    ks = get_keystore()
    result = []
    for p in DEFAULT_PROVIDERS:
        entry = dict(p)
        entry["has_key"] = ks.get_key(p["id"], "api_key") is not None
        entry["auth_status"] = get_browser_auth().get_auth_status(p["id"])
        entry["selected_model"] = ks.get_model_selection(p["id"])
        result.append(entry)
    return {"providers": result}


@app.post("/providers")
async def add_or_update_provider(req: KeyRequest):
    ks = get_keystore()
    ks.add_key(req.provider_id, req.key, req.key_type)
    return {"success": True, "message": f"Key saved for {req.provider_id}"}


@app.delete("/providers/{provider_id}")
async def remove_provider(provider_id: str, key_type: str = "api_key"):
    ks = get_keystore()
    removed = ks.remove_key(provider_id, key_type)
    return {"success": removed, "message": f"{'Removed' if removed else 'Not found'}"}


@app.get("/models")
async def list_models(provider: str = Query(...), free_only: bool = Query(False)):
    models = get_models_for_provider(provider, free_only=free_only)
    ks = get_keystore()
    selected = ks.get_model_selection(provider)
    return {
        "models": [m.__dict__ for m in models],
        "selected": selected,
    }


@app.get("/keys")
async def list_keys():
    ks = get_keystore()
    return {"keys": ks.list_all_keys()}


@app.post("/keys")
async def add_key(req: KeyRequest):
    ks = get_keystore()
    ks.add_key(req.provider_id, req.key, req.key_type)
    return {"success": True}


@app.delete("/keys/{provider_id}")
async def remove_key(provider_id: str, key_type: str = "api_key"):
    ks = get_keystore()
    removed = ks.remove_key(provider_id, key_type)
    return {"success": removed}


@app.post("/model-selection")
async def set_model_selection(req: ModelSelectionRequest):
    ks = get_keystore()
    ks.add_model_selection(req.provider_id, req.model)
    return {"success": True}


@app.post("/search-keys")
async def add_search_key(req: SearchKeyRequest):
    ks = get_keystore()
    ks.add_search_key(req.backend, req.key)
    return {"success": True}


@app.get("/search-keys")
async def list_search_keys():
    ks = get_keystore()
    result = {}
    for b in SEARCH_BACKENDS:
        key = ks.get_search_key(b)
        result[b] = {"configured": key is not None, "masked": ("***" + key[-4:]) if key and len(key) > 4 else None}
    return {"search_keys": result}


@app.post("/search-backend")
async def set_search_backend(req: SearchBackendRequest):
    if req.backend not in SEARCH_BACKENDS:
        raise HTTPException(status_code=400, detail=f"Invalid backend: {req.backend}")
    ks = get_keystore()
    ks.add_setting("active_search_backend", req.backend)
    return {"success": True}


@app.get("/search-backend")
async def get_search_backend():
    ks = get_keystore()
    return {"backend": ks.get_setting("active_search_backend", "tavily")}


@app.post("/api-check")
async def api_check(req: ApiCheckRequest):
    return test_provider_key(req.provider_id, req.model, req.base_url, req.use_browser_token)


@app.post("/api-check/tavily")
async def check_tavily():
    return test_tavily_key()


@app.post("/api-check/brave")
async def check_brave():
    return test_brave_key()


@app.post("/workspace/connect")
async def connect_workspace(req: WorkspaceConnectRequest):
    ws = get_workspace()
    return ws.connect(req.path)


@app.post("/workspace/disconnect")
async def disconnect_workspace():
    ws = get_workspace()
    ws.disconnect()
    return {"success": True}


@app.get("/workspace/tree")
async def workspace_tree():
    ws = get_workspace()
    return ws.get_file_tree()


@app.get("/workspace/status")
async def workspace_status():
    ws = get_workspace()
    return {"connected": ws.is_connected(), "root": str(ws.get_root()) if ws.is_connected() else None}


@app.get("/sandbox/status")
async def sandbox_status():
    sandbox = get_sandbox()
    return sandbox.get_status()


@app.post("/sessions/save")
async def save_session(req: SessionSaveRequest):
    mem = get_memory()
    sm = get_session_manager()
    ws = get_workspace()
    result = sm.save_session(
        req.session_id,
        req.task,
        req.provider,
        req.model,
        str(ws.get_root()) if ws.is_connected() else "",
        mem.conversation,
        mem.steps_completed,
        mem.files_created,
        mem.files_modified,
        mem.tool_calls_log,
        mem.get_summary(),
    )
    return result


@app.post("/sessions/load/{session_id}")
async def load_session(session_id: str):
    sm = get_session_manager()
    return sm.load_session(session_id)


@app.get("/sessions")
async def list_sessions():
    sm = get_session_manager()
    return sm.list_sessions()


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    sm = get_session_manager()
    return sm.delete_session(session_id)


@app.get("/stats")
async def get_stats_data():
    tracker = get_stats()
    return tracker.get_dashboard_data()


@app.get("/stats/current")
async def get_current_stats():
    tracker = get_stats()
    return tracker.get_current_stats()


@app.post("/diff")
async def compute_diff_endpoint(req: DiffRequest):
    return compute_diff(req.old_content, req.new_content, f"a/{req.file_path}", f"b/{req.file_path}")


@app.post("/diff/side-by-side")
async def compute_side_by_side_endpoint(req: DiffRequest):
    return compute_side_by_side(req.file_path, req.old_content, req.new_content)


@app.get("/git/status")
async def git_status():
    return get_git_tools().status()


@app.get("/git/log")
async def git_log(count: int = 10):
    return get_git_tools().log(count)


@app.get("/git/diff")
async def git_diff(file_path: Optional[str] = None):
    return get_git_tools().diff(file_path)


@app.get("/git/branch")
async def git_branch():
    return get_git_tools().branch_list()


@app.post("/git/init")
async def git_init():
    return get_git_tools().init()


@app.post("/git/commit")
async def git_commit(req: GitCommitRequest):
    return get_git_tools().commit_all(req.message)


@app.post("/git/branch")
async def git_branch_action(req: GitBranchRequest):
    git = get_git_tools()
    if req.action == "create":
        return git.create_branch(req.name)
    elif req.action == "checkout":
        return git.checkout(req.name)
    return {"success": False, "error": f"Unknown action: {req.action}"}


@app.post("/git/push")
async def git_push(remote: str = "origin"):
    return get_git_tools().push(remote)


@app.post("/memory/search")
async def search_memory(req: SearchMemoryRequest):
    return get_memory_search().search(req.query, req.limit)


@app.get("/memory/recent")
async def recent_memory(limit: int = 10):
    return get_memory_search().get_recent(limit)


@app.post("/memory/index/{session_id}")
async def index_memory(session_id: str):
    sm = get_session_manager()
    session = sm.load_session(session_id)
    if session.get("success"):
        data = session["session"]
        return get_memory_search().index_conversation(session_id, data.get("task", ""), data.get("conversation", []))
    return {"success": False, "error": "Session not found"}


@app.get("/update/check")
async def check_update(force: bool = False):
    return get_update_checker().check_for_updates(force)


@app.get("/update/version")
async def get_version():
    return {"version": get_update_checker().get_current_version()}


@app.get("/plugins")
async def list_plugins():
    return get_plugin_manager().list_plugins()


@app.post("/plugins/load/{name}")
async def load_plugin(name: str):
    return get_plugin_manager().load_plugin(name)


@app.post("/plugins/unload/{name}")
async def unload_plugin(name: str):
    return get_plugin_manager().unload_plugin(name)


@app.post("/plugins/install")
async def install_plugin(req: PluginInstallRequest):
    return get_plugin_manager().install_plugin(req.source_code, req.name)


@app.delete("/plugins/{name}")
async def uninstall_plugin(name: str):
    return get_plugin_manager().uninstall_plugin(name)


@app.post("/plugins/template")
async def create_plugin_template(req: PluginTemplateRequest):
    return get_plugin_manager().create_plugin_template(req.name)


@app.get("/mcp/servers")
async def list_mcp_servers():
    return get_mcp_manager().list_servers()


@app.post("/mcp/servers")
async def add_mcp_server(req: MCPServerRequest):
    return get_mcp_manager().add_server(req.name, req.command, req.args, req.env)


@app.delete("/mcp/servers/{name}")
async def remove_mcp_server(name: str):
    return get_mcp_manager().remove_server(name)


@app.get("/templates")
async def list_templates():
    return get_template_manager().list_templates()


@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    return get_template_manager().get_template(template_id)


@app.post("/templates/create")
async def create_from_template(req: TemplateCreateRequest):
    return get_template_manager().create_project(req.template_id, req.target_dir, req.project_name)


@app.post("/compose/up")
async def compose_up(req: ComposeUpRequest):
    return get_compose_manager().up(build=req.build)


@app.post("/compose/down")
async def compose_down():
    return get_compose_manager().down()


@app.post("/compose/stop")
async def compose_stop():
    return get_compose_manager().stop()


@app.post("/compose/restart")
async def compose_restart():
    return get_compose_manager().restart()


@app.get("/compose/ps")
async def compose_ps():
    return get_compose_manager().ps()


@app.get("/compose/logs")
async def compose_logs(service: str = "", lines: int = 100):
    return get_compose_manager().logs(service, lines)


@app.post("/compose/generate")
async def compose_generate(req: ComposeGenerateRequest):
    return get_compose_manager().generate_compose(req.services)


@app.post("/sandbox/start")
async def start_sandbox():
    sandbox = get_sandbox()
    return sandbox.start()


@app.post("/sandbox/stop")
async def stop_sandbox():
    sandbox = get_sandbox()
    return sandbox.stop()


@app.post("/sandbox/build")
async def build_sandbox():
    sandbox = get_sandbox()
    return sandbox.build_image()


@app.post("/auth/browser-login")
async def start_browser_login(req: BrowserLoginRequest):
    auth = get_browser_auth()
    return auth.start_browser_login(req.provider_id)


@app.get("/auth/status")
async def auth_status(provider_id: str = Query(...)):
    auth = get_browser_auth()
    return auth.get_auth_status(provider_id)


@app.post("/auth/manual-token")
async def save_manual_token(req: ManualTokenRequest):
    auth = get_browser_auth()
    return auth.save_manual_token(req.provider_id, req.token)


@app.post("/auth/oauth-callback")
async def oauth_callback(req: OAuthCallbackRequest):
    auth = get_browser_auth()
    return auth.complete_oauth_callback(req.provider_id, req.code, req.state)


@app.post("/auth/logout")
async def auth_logout(provider_id: str = Query(...)):
    auth = get_browser_auth()
    return auth.logout(provider_id)


@app.get("/export")
async def export_workspace():
    ws = get_workspace()
    if not ws.is_connected():
        raise HTTPException(status_code=400, detail="No workspace connected")
    files = ws.list_files_recursive()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            full_path = ws.get_root() / f
            zf.write(full_path, f)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=devin-workspace.zip"},
    )


@app.get("/auth/login-status")
async def auth_login_status(provider_id: str = Query(...)):
    auth = get_browser_auth()
    return auth.get_login_status(provider_id)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "run":
                if not _check_rate_limit():
                    await websocket.send_json({"event": "error", "message": "Rate limit exceeded. Try again later."})
                    continue

                task = msg.get("task", "")
                provider_id = msg.get("provider", "openai")
                model = msg.get("model", "gpt-4o")
                use_browser = msg.get("use_browser_token", False)
                context = msg.get("context", None)

                try:
                    provider = get_provider(provider_id, use_browser_token=use_browser)
                except Exception as e:
                    await websocket.send_json({"event": "error", "message": f"Provider error: {e}"})
                    continue

                global _orchestrator
                _orchestrator = Orchestrator(provider, model)

                try:
                    async for event in _orchestrator.run(task, context):
                        await websocket.send_json(event)
                except Exception as e:
                    await websocket.send_json({"event": "error", "message": f"Agent error: {e}"})
                    await websocket.send_json({"event": "workflow_done", "summary": ""})

            elif msg.get("type") == "control":
                action = msg.get("action", "")
                if _orchestrator:
                    if action == "pause":
                        _orchestrator.pause()
                        await websocket.send_json({"event": "paused"})
                    elif action == "resume":
                        _orchestrator.resume()
                        await websocket.send_json({"event": "resumed"})
                    elif action == "stop":
                        _orchestrator.stop()
                        await websocket.send_json({"event": "stopped"})

            elif msg.get("type") == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        if _orchestrator:
            _orchestrator.stop()
    except Exception:
        pass


@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()
    shell = None
    try:
        if os.name == "nt":
            shell = subprocess.Popen(
                ["cmd.exe"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            shell = subprocess.Popen(
                ["/bin/bash", "-i"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )

        async def read_output():
            loop = asyncio.get_event_loop()
            while True:
                data = await loop.run_in_executor(None, shell.stdout.readline)
                if not data:
                    break
                try:
                    text = data.decode("utf-8", errors="replace")
                except Exception:
                    text = str(data)
                await websocket.send_text(text)

        read_task = asyncio.create_task(read_output())

        while True:
            data = await websocket.receive_text()
            if shell.poll() is not None:
                await websocket.send_text("\r\n[Shell exited]\r\n")
                break
            if data == "\x03":
                shell.terminate()
                break
            try:
                shell.stdin.write(data.encode("utf-8"))
                shell.stdin.flush()
            except (BrokenPipeError, OSError):
                break

        read_task.cancel()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(f"\r\n[Terminal error: {e}]\r\n")
        except Exception:
            pass
    finally:
        if shell and shell.poll() is None:
            shell.terminate()


def main():
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")


if __name__ == "__main__":
    main()
