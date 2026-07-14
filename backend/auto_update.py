from __future__ import annotations
import json
import time
from typing import Any, Dict, List, Optional

import requests


GITHUB_REPO = "devin-clone/devin-clone"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "1.0.0"


class UpdateChecker:
    def __init__(self) -> None:
        self._last_check: float = 0
        self._check_interval: float = 3600
        self._latest_version: Optional[str] = None
        self._download_url: Optional[str] = None
        self._changelog: Optional[str] = None
        self._update_available: bool = False

    def check_for_updates(self, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and (now - self._last_check) < self._check_interval:
            return {
                "success": True,
                "update_available": self._update_available,
                "current_version": CURRENT_VERSION,
                "latest_version": self._latest_version,
                "download_url": self._download_url,
                "changelog": self._changelog,
                "cached": True,
            }

        try:
            resp = requests.get(GITHUB_API, timeout=10, headers={"Accept": "application/vnd.github.v3+json"})
            if resp.status_code == 200:
                data = resp.json()
                tag = data.get("tag_name", "").lstrip("v")
                self._latest_version = tag
                self._changelog = data.get("body", "")[:2000]
                assets = data.get("assets", [])
                self._download_url = data.get("html_url", "")
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if "windows" in name or name.endswith(".exe"):
                        self._download_url = asset.get("browser_download_url", self._download_url)
                        break
                self._update_available = self._is_newer(tag, CURRENT_VERSION)
                self._last_check = now
                return {
                    "success": True,
                    "update_available": self._update_available,
                    "current_version": CURRENT_VERSION,
                    "latest_version": tag,
                    "download_url": self._download_url,
                    "changelog": self._changelog,
                    "cached": False,
                }
            elif resp.status_code == 404:
                return {"success": True, "update_available": False, "current_version": CURRENT_VERSION, "message": "No releases found on GitHub", "cached": False}
            else:
                return {"success": False, "error": f"GitHub API returned {resp.status_code}"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "No internet connection"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _is_newer(self, latest: str, current: str) -> bool:
        try:
            def parse(v: str) -> List[int]:
                return [int(x) for x in v.replace("-", ".").split(".") if x.isdigit()]
            l = parse(latest)
            c = parse(current)
            return l > c
        except Exception:
            return latest != current

    def get_current_version(self) -> str:
        return CURRENT_VERSION


_update_checker = UpdateChecker()


def get_update_checker() -> UpdateChecker:
    return _update_checker
