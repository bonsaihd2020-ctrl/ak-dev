from __future__ import annotations
import json
import os
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

_KEY_FILE = "devin-clone-keystore.enc"
_SALT_FILE = "devin-clone-salt.bin"


def _keystore_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / "devin-clone"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _derive_key() -> bytes:
    import base64
    import hashlib
    machine_id = f"{platform.node()}-{os.getlogin() if hasattr(os, 'getlogin') else 'devin'}"
    digest = hashlib.sha256(machine_id.encode()).digest()
    return base64.urlsafe_b64encode(digest[:32])


class KeyStore:
    def __init__(self) -> None:
        self._dir = _keystore_dir()
        self._path = self._dir / _KEY_FILE
        self._fernet = Fernet(_derive_key())
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            raw = self._path.read_bytes()
            decrypted = self._fernet.decrypt(raw)
            self._data = json.loads(decrypted.decode("utf-8"))
        else:
            self._data = {}

    def _save(self) -> None:
        raw = json.dumps(self._data, indent=2).encode("utf-8")
        encrypted = self._fernet.encrypt(raw)
        self._path.write_bytes(encrypted)

    def add_key(self, provider_id: str, key: str, key_type: str = "api_key") -> None:
        if provider_id not in self._data:
            self._data[provider_id] = {}
        self._data[provider_id][key_type] = key
        self._save()

    def get_key(self, provider_id: str, key_type: str = "api_key") -> Optional[str]:
        return self._data.get(provider_id, {}).get(key_type)

    def remove_key(self, provider_id: str, key_type: str = "api_key") -> bool:
        if provider_id in self._data and key_type in self._data[provider_id]:
            del self._data[provider_id][key_type]
            if not self._data[provider_id]:
                del self._data[provider_id]
            self._save()
            return True
        return False

    def list_providers(self) -> List[str]:
        return list(self._data.keys())

    def list_all_keys(self) -> Dict[str, Dict[str, str]]:
        result = {}
        for pid, keys in self._data.items():
            result[pid] = {k: ("***" + v[-4:] if len(v) > 4 else "***") for k, v in keys.items()}
        return result

    def add_search_key(self, backend: str, key: str) -> None:
        self.add_key(f"search_{backend}", key, "search_key")

    def get_search_key(self, backend: str) -> Optional[str]:
        return self.get_key(f"search_{backend}", "search_key")

    def add_model_selection(self, provider_id: str, model: str) -> None:
        if provider_id not in self._data:
            self._data[provider_id] = {}
        self._data[provider_id]["selected_model"] = model
        self._save()

    def get_model_selection(self, provider_id: str) -> Optional[str]:
        return self._data.get(provider_id, {}).get("selected_model")

    def add_setting(self, key: str, value: Any) -> None:
        if "_settings" not in self._data:
            self._data["_settings"] = {}
        self._data["_settings"][key] = value
        self._save()

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self._data.get("_settings", {}).get(key, default)

    def export_all(self) -> Dict[str, Any]:
        return dict(self._data)


_store: Optional[KeyStore] = None


def get_keystore() -> KeyStore:
    global _store
    if _store is None:
        _store = KeyStore()
    return _store
