# integrator_patch_utils.py (nuovo file)
import os
import shutil
import py_compile
import datetime

BACKUP_DIR = "backup_files"
SANDBOX_DIR = "sandbox"

os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(SANDBOX_DIR, exist_ok=True)

def backup_file(original_path: str) -> str:
    """
    Salva una copia del file originale prima della patch.
    Ritorna il path del file backup.
    """
    filename = os.path.basename(original_path)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"{timestamp}_{filename}.bak")
    shutil.copy2(original_path, backup_path)
    return backup_path

def simulate_patch_on_copy(file_path: str, patch_line: str, new_code: str) -> bool:
    """
    Applica la patch in sandbox e verifica la compilazione.
    """
    sandbox_path = os.path.join(SANDBOX_DIR, os.path.basename(file_path))
    shutil.copy2(file_path, sandbox_path)

    try:
        with open(sandbox_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        patched = False
        with open(sandbox_path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line)
                if patch_line in line and not patched:
                    f.write(new_code + "\n")
                    patched = True

        py_compile.compile(sandbox_path, doraise=True)
        return True
    except Exception as e:
        print(f"[Sandbox] Patch fallita: {e}")
        return False

def validate_patch_effect(pre_metrics: dict, post_metrics: dict, threshold: float = 0.1) -> bool:
    """
    Confronta due snapshot metrici. Se peggioramento > threshold → rollback.
    """
    for key in pre_metrics:
        if key in post_metrics:
            drop = pre_metrics[key] - post_metrics[key]
            if drop > threshold:
                print(f"[Validation] Peggioramento metrica '{key}': -{drop:.2%}")
                return False
    return True
