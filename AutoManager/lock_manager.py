# lock_manager.py

import os
import json
import time
from AutoManager import settings_manager as mgr_set

LOCK_FILE = "integration_logs/param_locks.json"


def _load_locks():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def _save_locks(data):
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def is_param_locked(param: str) -> bool:
    locks = _load_locks()
    if param not in locks:
        return False
    last_time = locks[param]
    return (time.time() - last_time) < mgr_set.LOCK_COOLDOWN_SECONDS


def update_lock(param: str):
    locks = _load_locks()
    locks[param] = time.time()
    _save_locks(locks)


def clear_locks():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

# --- Estensione per lock su file+riga o file+location ---

def lock_file_location(file: str, loc: str):
    locks = _load_locks()
    key = f"{file}::{loc}"
    locks[key] = time.time()
    _save_locks(locks)


def is_file_location_locked(file: str, loc: str) -> bool:
    locks = _load_locks()
    key = f"{file}::{loc}"
    if key not in locks:
        return False
    return (time.time() - locks[key]) < mgr_set.LOCK_COOLDOWN_SECONDS


def unlock_file_location(file: str, loc: str):
    locks = _load_locks()
    key = f"{file}::{loc}"
    if key in locks:
        del locks[key]
        _save_locks(locks)


def get_active_locks():
    return _load_locks()
