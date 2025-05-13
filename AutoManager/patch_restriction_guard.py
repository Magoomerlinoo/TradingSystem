import sys
import json
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import ast
import hashlib
from typing import Dict
from TradingBot import settings  # Per FULL_PRODUCTION_MODE

BLACKLIST_PATH = "modification_logs/blacklist_patch_hashes.json"

# File critici protetti (modificabili solo in fase debug)
PROTECTED_FILES = [
    "run.py",
    "supervisor.py",
    "lock_manager.py",
    "patch_logger_sql.py"
]

# Parametri riservati
PROTECTED_PARAMS = [
    "API_KEY",
    "FULL_PRODUCTION_MODE",
    "TELEGRAM_CHAT_ID",
    "AUTO_APPLY_PATCHES"
]

def is_param_protected(param: str) -> bool:
    """
    Verifica se il parametro è riservato e non modificabile.
    Usa l'elenco PROTECTED_PARAMS definito localmente.
    """
    return param.strip().upper() in PROTECTED_PARAMS

def patch_modifies_protected_param(patch: dict) -> bool:
    """
    Se la patch modifica direttamente un parametro protetto via codice (riga di settings.py).
    """
    if patch.get("file") != "settings.py":
        return False

    code = patch.get("modification", {}).get("new_value", "")
    for protected in PROTECTED_PARAMS:
        if protected in code:
            return True
    return False

def is_file_protected(file_path: str) -> bool:
    """
    Blocca patch su file critici in produzione.
    """
    if settings.FULL_PRODUCTION_MODE:
        return file_path != "settings.py"  # Solo questo ammesso
    return file_path in PROTECTED_FILES


def is_param_locked(param: str) -> bool:
    """
    Blocca patch su parametri di sistema critici.
    """
    return param.upper() in PROTECTED_PARAMS


def get_patch_hash(patch: Dict) -> str:
    """
    Calcola hash SHA256 stabile del contenuto patch.
    """
    string = json.dumps(patch, sort_keys=True)
    return hashlib.sha256(string.encode()).hexdigest()


def is_patch_blacklisted(patch: Dict) -> bool:
    """
    Verifica se la patch è già stata bannata per fallimenti precedenti.
    """
    if not os.path.exists(BLACKLIST_PATH):
        return False
    with open(BLACKLIST_PATH, encoding="utf-8") as f:
        hashes = json.load(f)
    return get_patch_hash(patch) in hashes


def add_to_blacklist(patch: Dict):
    """
    Registra la patch nella blacklist se non già presente.
    """
    h = get_patch_hash(patch)
    if os.path.exists(BLACKLIST_PATH):
        with open(BLACKLIST_PATH, encoding="utf-8") as f:
            hashes = json.load(f)
    else:
        hashes = []
    if h not in hashes:
        hashes.append(h)
        with open(BLACKLIST_PATH, "w", encoding="utf-8") as f:
            json.dump(hashes, f, indent=2)


def validate_ast_patch(patch: Dict) -> bool:
    """
    Verifica che la patch sia sintatticamente valida via AST.
    """
    try:
        code = patch.get("modification", {}).get("new_value")
        if not code:
            return True  # Nessun codice da validare
        ast.parse(code)
        return True
    except Exception:
        return False
