import os
import shutil
import subprocess
import tempfile
import json
import ast
from pathlib import Path
from typing import Dict


def run_sandbox_test(patch: Dict, project_root: str = "../") -> Dict:
    file_rel_path = patch.get("file")
    mod = patch.get("modification")
    if not file_rel_path or not mod:
        return {"patch_validated": False, "error": "Patch incompleta"}

    full_file_path = os.path.join(project_root, file_rel_path)
    if not os.path.exists(full_file_path):
        return {"patch_validated": False, "error": f"File non trovato: {full_file_path}"}

    with tempfile.TemporaryDirectory() as sandbox_dir:
        sandbox_file_path = os.path.join(sandbox_dir, os.path.basename(file_rel_path))
        shutil.copy(full_file_path, sandbox_file_path)

        try:
            apply_patch_to_file(sandbox_file_path, mod)
        except Exception as e:
            return {"patch_validated": False, "error": f"Errore applicazione patch: {e}"}

        try:
            with open(sandbox_file_path, encoding="utf-8") as f:
                code = f.read()
            ast.parse(code)
        except SyntaxError as e:
            return {
                "patch_validated": False,
                "error": f"Errore di sintassi: {e}",
                "fallback_context": {
                    "file": file_rel_path,
                    "code": code,
                    "exception": str(e)
                }
            }

        try:
            result = subprocess.run(
                ["python", sandbox_file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return {
                    "patch_validated": False,
                    "error": f"Errore runtime: {result.stderr.strip() or 'exit code != 0'}",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
        except subprocess.TimeoutExpired:
            return {"patch_validated": False, "error": "Timeout esecuzione sandbox"}

    return {"patch_validated": True}


def apply_patch_to_file(file_path: str, modification: Dict) -> None:
    location = modification.get("location", {})
    line_type = location.get("type")
    line_val = location.get("value")
    old = modification.get("old_value", "").strip()
    new = modification.get("new_value", "")

    if line_type != "line" or not isinstance(line_val, (int, str)):
        raise ValueError("Solo patch line-based supportate")

    line_num = int(line_val) - 1

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not (0 <= line_num < len(lines)):
        raise IndexError("Indice di linea fuori range")

    if old and old not in lines[line_num]:
        raise ValueError("old_value non corrisponde alla linea corrente")

    lines[line_num] = new + "\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)