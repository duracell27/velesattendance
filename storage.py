import json
import asyncio
from pathlib import Path
from typing import Any
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType


class JsonStorage(BaseStorage):
    def __init__(self, path: str = "fsm_storage.json"):
        self._path = Path(path)
        self._lock = asyncio.Lock()
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data))

    def _key(self, key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        async with self._lock:
            k = self._key(key)
            if k not in self._data:
                self._data[k] = {}
            self._data[k]["state"] = state.state if hasattr(state, "state") else state
            self._save()

    async def get_state(self, key: StorageKey) -> str | None:
        async with self._lock:
            return self._data.get(self._key(key), {}).get("state")

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        async with self._lock:
            k = self._key(key)
            if k not in self._data:
                self._data[k] = {}
            self._data[k]["data"] = data
            self._save()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        async with self._lock:
            return dict(self._data.get(self._key(key), {}).get("data") or {})

    async def close(self) -> None:
        pass
