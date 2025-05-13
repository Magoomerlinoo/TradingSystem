# integrator.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import shutil
import datetime
import re
import ast
# === Configurazione percorsi ===
BASE_DIR              = os.path.dirname(__file__)
BOT_PATH              = os.path.abspath(os.path.join(BASE_DIR, "..", "TradingBot"))
MOD_JSON_PATH         = os.path.join(BASE_DIR, "modification_logs", "json")
PROCESSED_JSON_PATH   = os.path.join(BASE_DIR, "modification_logs", "processed")
INTEGRATION_LOGS_PATH = os.path.join(BASE_DIR, "integration_logs")

# === File critici che richiedono riavvio dopo patch ===
CRITICAL_RESTART_FILES = ["bot.py", "supervisor.py", "settings.py"]

# === Creazione cartelle se mancanti ===
for p in (MOD_JSON_PATH, PROCESSED_JSON_PATH, INTEGRATION_LOGS_PATH):
    os.makedirs(p, exist_ok=True)

from AutoManager.runtime_patch_manager import apply_runtime_reload
from AutoManager.validator import validate_python_file
from AutoManager.telegram_notifier import send_telegram_message
from AutoManager import settings_manager as mgr_set
from TradingBot import settings
from AutoManager.utils.sandbox_runner import run_sandbox_test
from AutoManager.utils.snapshot_logger import save_metric_snapshot
from AutoManager.lock_manager import is_param_locked
from AutoManager.performance_metrics import load_recent_trades, update_bot_stats
from AutoManager.utils.rollback_manager import create_reverse_patch
from AutoManager.utils.snapshot_logger import log_patch
from AutoManager.performance_metrics import update_bot_stats
from AutoManager.patch_restriction_guard import is_param_protected, is_file_protected, patch_modifies_protected_param
from AutoManager.blacklist_manager import is_patch_blacklisted, add_to_blacklist

def extract_function_names(code: str) -> set:
    try:
        tree = ast.parse(code)
        return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    except SyntaxError:
        return set()

# ------------------------------------------------------------
def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def absolute_bot_file(rel_path: str) -> str:
    return os.path.join(BOT_PATH, rel_path)

# ------------------------------------------------------------
def load_json_suggestions() -> list[tuple[str, dict]]:
    """
    Ritorna lista di (nome_file.json, contenuto_dict) pronti per essere processati.
    """
    out = []
    for fn in os.listdir(MOD_JSON_PATH):
        if fn.endswith(".json"):
            fp = os.path.join(MOD_JSON_PATH, fn)
            try:
                with open(fp, encoding="utf-8") as f:
                    suggestion = json.load(f)
                out.append((fn, suggestion))
            except Exception as e:
                print(f"[Integrator] Impossibile leggere {fn}: {e}")
    return out

# ------------------------------------------------------------
def replace_setting(file_path: str, param: str, new_val) -> tuple[bool,int|None,str|None]:
    """
    Modifica un parametro in settings.py.
    Ritorna (success, line_number, old_line).
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        new_lines, found, ln_no, old_line = [], False, None, None
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith(f"{param} ") or s.startswith(f"{param}="):
                found, ln_no, old_line = True, idx, line.rstrip()
                prefix = line.split("=")[0].rstrip()
                new_lines.append(f"{prefix} = {repr(new_val)}\n")
            else:
                new_lines.append(line)

        if not found:
            return False, None, None

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True, ln_no, old_line

    except Exception as e:
        print(f"[Integrator] Errore in replace_setting: {e}")
        return False, None, None

# ------------------------------------------------------------
def apply_code_patch(sug: dict, current_equity: float = None) -> tuple[bool, object, str, str, str]:
    """
    Applica patch generica su file di codice.
    Ritorna (success, location, old_snippet, new_snippet, loc_type).
    """
    sandbox_result = run_sandbox_test(sug)
    if not sandbox_result.get("patch_validated"):
        print(f"[Sandbox] Patch fallita: {sandbox_result['error']}")
        return False, None, None, None, "sandbox"

    rel_file = sug.get("file")
    mod = sug.get("modification", {})
    if not rel_file or not mod:
        return False, None, None, None, "undefined"

    # Snapshot metrica (se definita e non lockata)
    metric = sug.get("metric")
    if metric and not is_param_locked(metric) and current_equity is not None:
        recent_trades = load_recent_trades()
        current_stats = update_bot_stats(recent_trades, current_equity)
        current_value = current_stats.get(metric.lower())
        if current_value is not None:
            save_metric_snapshot(metric, current_value)

    target = absolute_bot_file(rel_file)
    if not os.path.isfile(target):
        print(f"[Integrator] File non trovato: {target}")
        return False, None, None, None, "undefined"

    action     = mod.get("action")
    loc_cfg    = mod.get("location", {})
    loc_type   = loc_cfg.get("type", "string")
    loc_val    = loc_cfg.get("value")
    old_check  = mod.get("old_value")
    new_code   = mod.get("new_value") or mod.get("content", "")

    # PATCH INTERO FILE
    if loc_type == "full_file":
        try:
            with open(target, encoding="utf-8") as f:
                old_code = f.read()

            ast.parse(new_code)
            old_funcs = extract_function_names(old_code)
            new_funcs = extract_function_names(new_code)
            required = {"main", "run", "start", "supervise"}
            missing = required.intersection(old_funcs) - new_funcs

            if missing:
                print(f"[Integrator] Patch rifiutata: funzioni essenziali rimosse: {missing}")
                return False, None, None, None, "full_file"

            with open(target, "w", encoding="utf-8") as f:
                f.write(new_code.strip() + "\n")

            return True, "FULL", "(intero file)", "(patchata)", "full_file"

        except SyntaxError as e:
            print(f"[Integrator] Nuovo codice invalido: {e}")
            return False, None, None, None, "full_file"

    # PATCH PARZIALE — LINE/REGEX/STRING
    with open(target, encoding="utf-8") as f:
        lines = f.readlines()

    out, changed = [], False
    log_line, old_snap, new_snap = None, None, None

    for idx, line in enumerate(lines, 1):
        if loc_type == "line":
            hit = (idx == int(loc_val))
        elif loc_type == "regex":
            hit = bool(re.search(loc_val, line))
        else:  # string
            hit = (loc_val in line)

        if not hit:
            out.append(line)
            continue

        if old_check and old_check not in line:
            print(f"[Integrator] old_value mismatch a riga {idx}")
            return False, loc_val, None, None, loc_type

        if action == "delete":
            changed = True
            old_snap = line.rstrip()
            log_line = idx if loc_type == "line" else loc_val
            continue

        if action == "insert":
            out.append(line)
            if new_code:
                out.append(new_code + "\n")
            changed = True
            log_line = idx if loc_type == "line" else loc_val
            old_snap = "(n/a)"
            new_snap = new_code
            continue

        if action == "replace":
            if new_code:
                out.append(new_code + "\n")
                changed = True
                log_line = idx if loc_type == "line" else loc_val
                old_snap = line.rstrip()
                new_snap = new_code
            continue

        out.append(line)

    if not changed:
        return False, None, None, None, loc_type

    with open(target, "w", encoding="utf-8") as f:
        f.writelines(out)

    return True, log_line, old_snap, new_snap, loc_type
# ------------------------------------------------------------
def save_log(
    json_name: str,
    file_mod: str,
    loc,
    loc_type: str,
    old,
    new,
    reason: str,
    patch_type: str,
    param: str = None,
    engine_used: str = "gpt-4-turbo"
):
    """
    Scrive un log dettagliato in INTEGRATION_LOGS_PATH.
    """
    ts_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_fn = f"integration_{ts_str}_{json_name.replace('.json','.txt')}"
    log_fp = os.path.join(INTEGRATION_LOGS_PATH, log_fn)

    with open(log_fp, "w", encoding="utf-8") as f:
        f.write("=== MODIFICA INTEGRAZIONE - AutoManager ===\n")
        f.write(f"Timestamp         : {timestamp()}\n")
        f.write(f"Sorgente JSON     : {json_name}\n")
        f.write(f"Motore GPT        : {engine_used}\n")
        f.write(f"Tipo patch        : {patch_type}\n")
        f.write(f"File interessato  : {file_mod}\n")
        f.write(f"Match type        : {loc_type}\n")
        f.write(f"Location / Riga   : {loc}\n")
        if param:
            f.write(f"Parametro         : {param}\n")
        if old is not None:
            f.write(f"Valore precedente : {old}\n")
        if new is not None:
            f.write(f"Valore nuovo      : {new}\n")
        f.write("\nMotivazione:\n")
        for line in reason.splitlines():
            f.write(f"  {line}\n")
        f.write("\n========================================\n")

    print(f"[Integrator] Log salvato -> integration_logs/{log_fn}")

# ------------------------------------------------------------
def log_error(param_name: str, message: str):
    """
    Aggiunge una riga di errore in integration_errors.log.
    """
    error_fp = os.path.join(INTEGRATION_LOGS_PATH, "integration_errors.log")
    with open(error_fp, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp()}] {param_name}: {message}\n")

# ------------------------------------------------------------
def process_suggestions(current_equity: float = None):
    """
    Cicla su tutti i JSON in MOD_JSON_PATH e applica patches o param updates.
    """
    suggestions = load_json_suggestions()
    if not suggestions:
        print("[Integrator] Nessun suggerimento JSON.")
        return

    for json_name, sug in suggestions:
        success    = False
        reason     = sug.get("reason", "")
        engine_used= sug.get("engine_used", "gpt-4-turbo")

        # ——— PARAM UPDATE ———
        if "param_to_modify" in sug:
            param   = sug["param_to_modify"]
            if is_param_protected(param):
                send_telegram_message(f"🔒 Parametro `{param}` non modificabile. Patch bloccata.")
                continue
            new_val = sug["new_value"]
            target_rel = sug.get("target_file", "settings.py")
            target_py  = absolute_bot_file(target_rel)

            ok, ln, old = replace_setting(target_py, param, new_val)
            if ok:
                save_log(json_name, target_py, ln, "param", old, f"{param} = {new_val}",
                         reason, "param_update", param, engine_used)
                success = True
            else:
                log_error(param, "Param non trovato o errore aggiornamento settings.py")

        # ——— CODE PATCH ———
        elif sug.get("file") and sug.get("modification"):

            if patch_modifies_protected_param(sug):
                send_telegram_message("🔒 Patch bloccata: modifica a parametro protetto in settings.py.")
                continue

            if is_file_protected(sug.get("file", "")):
                send_telegram_message("⚠️ Patch bloccata: file non modificabile.")
                continue

            if is_patch_blacklisted(sug):
                send_telegram_message("🚫 Patch già fallita in passato. Skippata.")
                continue

            # 1. Validazione AST prima di procedere
            if not validate_ast_patch(sug):
                send_telegram_message("🚫 Codice non valido (AST). Patch rifiutata.")
                add_to_blacklist(sug)
                continue

            # 2. Lock preventivo su stessa posizione
            rel_file = sug.get("file")
            mod      = sug.get("modification", {})
            loc      = mod.get("location", {})
            loc_val  = str(loc.get("value", ""))  # sempre stringa

            if is_file_location_locked(rel_file, loc_val):
                print(f"[Integrator] 🔒 Patch bloccata: {rel_file}::{loc_val}")
                continue

            # 3. Applica patch
            ok, loc, old, new, loc_type = apply_code_patch(sug, current_equity=current_equity)
            file_to_validate = absolute_bot_file(rel_file)

            if ok and validate_python_file(file_to_validate):
                apply_runtime_reload(rel_file)
                rel_file = sug["file"]
                reverse = create_reverse_patch(sug)
                log_patch(
                    file=rel_file,
                    metric=sug.get("metric", "UNDEFINED"),
                    patch=sug,
                    reverse=reverse,
                    status="success"
                )
                save_log(json_name, file_to_validate, loc, loc_type,
                        old, new, reason, "code_patch", None, engine_used)
                success = True
                critical = any(crit in rel_file for crit in CRITICAL_RESTART_FILES)

                if mgr_set.AUTO_APPLY_PATCHES:
                    if critical:
                        send_telegram_message(f"📦 Patch `{json_name}` applicata ma riavvio richiesto per attivarla (`{rel_file}`)")
                    else:
                        send_telegram_message(f"✅ Patch `{json_name}` applicata correttamente.")
                else:
                    send_telegram_message(f"📦 Patch `{json_name}` pronta. AUTO_APPLY_PATCHES = False → Riavvio richiesto.")

            else:
                log_error(sug.get("file"), "Patch fallita: validazione codice non superata")


        else:
            log_error(json_name, "Formato JSON non valido")

        # ——— Sposta solo se successo ———
        src = os.path.join(MOD_JSON_PATH, json_name)
        dst = os.path.join(PROCESSED_JSON_PATH, json_name)
        if success:
            try:
                shutil.move(src, dst)
                print(f"[Integrator] {json_name} → processed/")
            except Exception as e:
                print(f"[Integrator] Impossibile spostare {json_name}: {e}")
        else:
            print(f"[Integrator] {json_name} lasciato in coda; patch fallita.")

# ------------------------------------------------------------
def integrate_modification(_=None):
    print("[Integrator] Avvio integrazione...")
    process_suggestions()
    print("[Integrator] Fine integrazione.")

if __name__ == "__main__":
    equity_val = float(input("Equity attuale per snapshot: "))
    process_suggestions(current_equity=equity_val)