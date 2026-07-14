from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from config import CONTAINER_NAME, CONTAINER_IMAGE, NOVNC_PORT, VNC_PORT, SANDBOX_WORKSPACE


class SandboxManager:
    def __init__(self) -> None:
        self._running = False
        self._docker_available: Optional[bool] = None

    def check_docker(self) -> bool:
        if self._docker_available is not None:
            return self._docker_available
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._docker_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._docker_available = False
        return self._docker_available

    def is_running(self) -> bool:
        if not self.check_docker():
            return False
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._running = result.stdout.strip().lower() == "true"
        except Exception:
            self._running = False
        return self._running

    def start(self) -> Dict[str, Any]:
        if not self.check_docker():
            return {"success": False, "error": "Docker is not available. Please install Docker Desktop and ensure it is running."}
        if self.is_running():
            return {"success": True, "message": "Sandbox already running"}
        try:
            result = subprocess.run(
                ["docker", "run", "-d",
                 "--name", CONTAINER_NAME,
                 "-p", f"{NOVNC_PORT}:6080",
                 "-p", f"{VNC_PORT}:5900",
                 "--cap-add", "SYS_ADMIN",
                 "--security-opt", "seccomp=unconfined",
                 CONTAINER_IMAGE],
                capture_output=True, text=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                self._running = True
                return {"success": True, "container_id": result.stdout.strip(), "novnc_url": f"http://localhost:{NOVNC_PORT}/vnc.html"}
            return {"success": False, "error": f"Docker error: {result.stderr}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop(self) -> Dict[str, Any]:
        if not self.check_docker():
            return {"success": False, "error": "Docker not available"}
        try:
            subprocess.run(
                ["docker", "stop", CONTAINER_NAME],
                capture_output=True, text=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            subprocess.run(
                ["docker", "rm", CONTAINER_NAME],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._running = False
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def exec_command(self, command: str, timeout: int = 60) -> Dict[str, Any]:
        if not self.is_running():
            return {"success": False, "error": "Sandbox not running"}
        try:
            result = subprocess.run(
                ["docker", "exec", "-i", CONTAINER_NAME, "bash", "-c", command],
                capture_output=True, text=True, timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sync_workspace(self, local_path: Optional[Path] = None) -> Dict[str, Any]:
        if not self.is_running():
            return {"success": False, "error": "Sandbox not running"}
        if local_path is None:
            return {"success": False, "error": "No workspace path provided"}
        try:
            result = subprocess.run(
                ["docker", "cp", str(local_path) + "/.", f"{CONTAINER_NAME}:{SANDBOX_WORKSPACE}/"],
                capture_output=True, text=True, timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Synced {local_path} to sandbox"}
            return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def pull_back_workspace(self, local_path: Optional[Path] = None) -> Dict[str, Any]:
        if not self.is_running():
            return {"success": False, "error": "Sandbox not running"}
        if local_path is None:
            return {"success": False, "error": "No workspace path provided"}
        try:
            result = subprocess.run(
                ["docker", "cp", f"{CONTAINER_NAME}:{SANDBOX_WORKSPACE}/.", str(local_path) + "/"],
                capture_output=True, text=True, timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Synced sandbox workspace back to {local_path}"}
            return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        docker_ok = self.check_docker()
        running = self.is_running() if docker_ok else False
        return {
            "docker_available": docker_ok,
            "sandbox_running": running,
            "novnc_url": f"http://localhost:{NOVNC_PORT}/vnc.html" if running else None,
            "container_name": CONTAINER_NAME,
        }

    def build_image(self) -> Dict[str, Any]:
        sandbox_dir = Path(__file__).parent.parent / "sandbox"
        if not (sandbox_dir / "Dockerfile").exists():
            return {"success": False, "error": f"No Dockerfile found at {sandbox_dir}"}
        try:
            result = subprocess.run(
                ["docker", "build", "-t", CONTAINER_IMAGE, str(sandbox_dir)],
                capture_output=True, text=True, timeout=300,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Image {CONTAINER_IMAGE} built successfully"}
            return {"success": False, "error": result.stderr[-500:]}
        except Exception as e:
            return {"success": False, "error": str(e)}


_sandbox = SandboxManager()


def get_sandbox() -> SandboxManager:
    return _sandbox
