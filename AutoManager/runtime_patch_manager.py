#runtime_patch_manager.py

import importlib
import sys

patch_history = []

def apply_runtime_reload(rel_path: str):
    """
    Ricarica dinamicamente il modulo Python indicato da un path relativo.
    Esempio: rel_path = "bot.py" → ricarica modulo 'bot'.
    """
    module_path = rel_path.replace("/", ".").replace("\\", ".").rstrip(".py")

    if module_path not in sys.modules:
        print(f"[RuntimePatch] 💤 Modulo non attivo o mai importato: {module_path}")
        return False

    try:
        importlib.reload(sys.modules[module_path])
        patch_history.append(module_path)
        print(f"[RuntimePatch] ✅ Reload completato: {module_path}")
        return True
    except Exception as e:
        print(f"[RuntimePatch] ⚠️ Errore durante reload {module_path}: {e}")
        return False

def get_patch_history() -> list:
    """Restituisce la cronologia dei moduli ricaricati."""
    return patch_history.copy()
