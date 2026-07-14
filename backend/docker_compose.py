from __future__ import annotations
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class DockerComposeManager:
    def __init__(self) -> None:
        self._project_dir: Optional[str] = None
        self._running_services: Dict[str, str] = {}

    def set_project_dir(self, path: str) -> None:
        self._project_dir = path

    def _run(self, args: List[str], timeout: int = 120) -> Dict[str, Any]:
        if not self._project_dir:
            return {"success": False, "error": "No project directory set"}
        try:
            result = subprocess.run(
                ["docker-compose"] + args,
                cwd=self._project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except FileNotFoundError:
            result = subprocess.run(
                ["docker", "compose"] + args,
                cwd=self._project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def has_compose_file(self) -> bool:
        if not self._project_dir:
            return False
        p = Path(self._project_dir)
        return any((p / name).exists() for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"])

    def up(self, build: bool = True, detach: bool = True) -> Dict[str, Any]:
        args = ["up"]
        if build:
            args.append("--build")
        if detach:
            args.append("-d")
        return self._run(args, timeout=300)

    def down(self) -> Dict[str, Any]:
        return self._run(["down"], timeout=60)

    def stop(self) -> Dict[str, Any]:
        return self._run(["stop"], timeout=60)

    def start(self) -> Dict[str, Any]:
        return self._run(["start"], timeout=60)

    def restart(self) -> Dict[str, Any]:
        return self._run(["restart"], timeout=60)

    def logs(self, service: str = "", lines: int = 100) -> Dict[str, Any]:
        args = ["logs", "--tail", str(lines)]
        if service:
            args.append(service)
        return self._run(args, timeout=30)

    def ps(self) -> Dict[str, Any]:
        result = self._run(["ps"], timeout=15)
        if result.get("success"):
            services = []
            for line in result["stdout"].split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    services.append({
                        "name": parts[0],
                        "command": parts[1] if len(parts) > 1 else "",
                        "status": parts[2] if len(parts) > 2 else "",
                        "ports": parts[3] if len(parts) > 3 else "",
                    })
            result["services"] = services
        return result

    def exec_command(self, service: str, command: str) -> Dict[str, Any]:
        return self._run(["exec", "-T", service, "bash", "-c", command], timeout=60)

    def generate_compose(self, services: List[Dict[str, Any]]) -> Dict[str, Any]:
        compose = {"version": "3.8", "services": {}}
        for svc in services:
            name = svc.get("name", "service")
            compose["services"][name] = {
                "image": svc.get("image", "ubuntu:22.04"),
                "ports": svc.get("ports", []),
                "environment": svc.get("environment", {}),
                "volumes": svc.get("volumes", []),
                "depends_on": svc.get("depends_on", []),
            }
            if svc.get("build"):
                compose["services"][name]["build"] = svc["build"]
        try:
            if self._project_dir:
                path = Path(self._project_dir) / "docker-compose.yml"
                path.write_text(json.dumps(compose, indent=2), encoding="utf-8")
                return {"success": True, "path": str(path), "compose": compose}
            return {"success": False, "error": "No project directory set"}
        except Exception as e:
            return {"success": False, "error": str(e)}


_compose_manager = DockerComposeManager()


def get_compose_manager() -> DockerComposeManager:
    return _compose_manager
