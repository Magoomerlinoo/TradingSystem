# validator.py
import ast
import importlib.util
import traceback


def validate_python_file(filepath: str) -> bool:
    """
    Verifica che un file Python:
    1. Sia sintatticamente corretto
    2. Possa essere importato senza errori
    """
    try:
        # ✅ Verifica sintattica
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        ast.parse(source)  # Syntax Check

        # ✅ Verifica importabilità dinamica
        module_name = "patch_validation_temp"
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return True

    except Exception as e:
        print("[Validator] Errore validazione patch:", e)
        traceback.print_exc()
        return False
