import os
import json
from datetime import datetime
from typing import Dict


def create_reverse_patch(patch: Dict) -> Dict:
    """
    Genera un reverse_patch dal patch originale.
    """
    rev = {
        "action": patch["modification"]["action"],
        "location": patch["modification"]["location"],
        "old_value": patch["modification"]["new_value"],
        "new_value": patch["modification"]["old_value"]
    }
    return {
        "file": patch["file"],
        "modification": rev
    }


def save_reverse_patch(original_patch: Dict, output_dir: str = "modification_logs/reverse") -> str:
    """
    Salva il reverse_patch su disco in formato JSON.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    patch_id = f"rollback_{ts}"
    file_name = f"{patch_id}.json"
    path = os.path.join(output_dir, file_name)

    reverse = create_reverse_patch(original_patch)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reverse, f, indent=2)

    return path


def apply_reverse_patch_file(file_path: str) -> bool:
    """
    Applica un reverse_patch da file JSON.
    """
    if not os.path.isfile(file_path):
        return False

    with open(file_path, encoding="utf-8") as f:
        patch = json.load(f)

    from AutoManager.integrator import apply_code_patch
    success, *_ = apply_code_patch(patch)
    return success
