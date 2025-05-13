# supervisor.py

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import logging
import json
import ast
import datetime
import sys
import settings_manager as mgr_set
from TradingBot import settings
from AutoManager.lock_manager import is_param_locked
from AutoManager.agent import parse_and_save_suggestion
from AutoManager.utils.meta_metric_analyzer import generate_context_for_gpt
from integrator import integrate_modification
from AutoManager.utils.rollback_manager import save_reverse_patch, apply_reverse_patch_file
from github_uploader import git_add_commit_push
from telegram_notifier import send_telegram_message
from AutoManager.utils.context_builder import build_prompt_context
from performance_metrics import update_bot_stats
from patch_batch_manager import apply_batch_patches
from AutoManager.utils.trade_tracker import load_recent_trades
from telegram_notifier import send_telegram_message
from AutoManager.utils.sandbox_runner import run_sandbox_test
from lock_manager import unlock_param
import glob
LAST_PATCH_PATH = os.path.join(os.path.dirname(__file__), "modification_logs/last_patch.json")

PATCH_SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "patch_snapshot")
os.makedirs(PATCH_SNAPSHOT_DIR, exist_ok=True)

from AutoManager.utils.patch_logger_sql import mark_patch_status, get_latest_patch_id


def auto_debug_and_repair(file_path: str, error_msg: str) -> bool:
    """
    Entry point per autodebug del sistema.
    - file_path: file fallito
    - error_msg: messaggio di errore originale
    Ritorna True se patch applicata e validata, False altrimenti.
    """

    from AutoManager.openai_manager import generate_patch_from_context
    from AutoManager.integrator import apply_code_patch
    from AutoManager.utils.sandbox_runner import run_sandbox_test
    from AutoManager.validator import validate_python_file
    from AutoManager.telegram_notifier import send_telegram_message
    from utils.context_builder import build_prompt_context

    if not os.path.exists(file_path):
        send_telegram_message(f"❌ File crashato non trovato: {file_path}")
        return False

    try:
        with open(file_path, encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        send_telegram_message(f"❌ Lettura file fallita: {file_path}\n{e}")
        return False

    context_str = build_prompt_context()
    fallback_context = {
        "file": file_path,
        "code": code,
        "error": error_msg,
        "prompt_context": context_str,
        "fallback_mode": True
    }

    patch = generate_patch_from_context(fallback_context)
    if not patch or "modification" not in patch:
        send_telegram_message(f"❌ Patch non generata per `{file_path}`.")
        return False

    ok, loc, old, new, loc_type = apply_code_patch(patch)
    if not ok:
        send_telegram_message(f"❌ Applicazione patch fallita su `{file_path}`.")
        return False

    if not validate_python_file(file_path):
        send_telegram_message(f"❌ Validazione fallita dopo patch su `{file_path}`.")
        return False

    sandbox_result = run_sandbox_test(patch)
    if not sandbox_result.get("patch_validated"):
        err = sandbox_result.get("error", "Errore non specificato")
        send_telegram_message(f"❌ Sandbox fallita: {err}")
        return False

    send_telegram_message(f"✅ Patch fallback correttamente applicata e validata per `{file_path}`.")
    return True

def try_fix_file(file_path: str):
    """
    Verifica se il file ha errori e prova a correggerlo automaticamente.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            code = f.read()
        ast.parse(code)
        print(f"[Supervisor] ✅ Nessun errore in {file_path}")
    except SyntaxError as e:
        print(f"[Supervisor] ⚠️ SyntaxError in {file_path}")
        handle_crash_and_generate_patch(file_path=file_path, error=str(e), code=code)

def process_patch_file(patch):
    from openai_manager import generate_patch_from_context
    from integrator import apply_code_patch
    from AutoManager.utils.sandbox_runner import run_sandbox_test
    from AutoManager.utils.patch_logger_sql import mark_patch_status, get_latest_patch_id

    file_path = patch.get("file")
    modification = patch.get("modification")
    if not file_path or not modification:
        send_telegram_message("⚠️ Patch invalida, mancano `file` o `modification`.")
        return None

    full_path = os.path.join("..", file_path)

    try:
        with open(full_path, encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        send_telegram_message(f"❌ File non trovato: {file_path}")
        return None

    # Fallback se il file è corrotto
    try:
        ast.parse(code)
    except SyntaxError as e:
        fallback_context = {
            "file": file_path,
            "code": code,
            "error": str(e),
            "reason": "SyntaxError",
            "fallback_mode": True
        }
        send_telegram_message(f"🔁 Patch AST fallback in corso su `{file_path}`")
        patch = generate_patch_from_context(fallback_context)

        if not patch or "modification" not in patch:
            send_telegram_message("❌ Fallback GPT non ha generato una patch valida.")
            return None

    # Blocco modalità produzione
    if mgr_set.FULL_PRODUCTION_MODE and patch.get("modification_type") == "code_patch":
        send_telegram_message("🛑 FULL_PRODUCTION_MODE attivo → Patch codice non applicata.")
        return None

    # Applica patch
    success, loc, old, new, loc_type = apply_code_patch(patch)
    if not success:
        send_telegram_message(f"❌ Applicazione patch fallita su `{file_path}`.")
        return None

    # Sandbox test
    test_result = run_sandbox_test(patch, project_root="..")
    if not test_result.get("patch_validated", False):
        err = test_result.get("error", "Errore non specificato")
        send_telegram_message(f"❌ Patch non valida in sandbox: {file_path} - {err}")
        return None

    # Snapshot patch per rollback
    with open(LAST_PATCH_PATH, "w", encoding="utf-8") as f:
        json.dump(patch, f, indent=2)

    # Log patch SQL
    patch_id = get_latest_patch_id(patch.get("metric", "UNDEFINED"))
    mark_patch_status(patch_id, "applied")

    send_telegram_message(f"✅ Patch validata e applicata su `{file_path}`.")
    return patch

def evaluate_patch_result_and_decide(metric_name: str, current_equity: float):
    """
    Confronta lo snapshot salvato prima della patch con i dati attuali.
    Esegue rollback se le performance sono peggiorate.
    """
    try:
        files = sorted(glob.glob(os.path.join(PATCH_SNAPSHOT_DIR, f"*_{metric_name}.json")), reverse=True)
        if not files:
            send_telegram_message("⚠️ Nessuno snapshot trovato per confronto patch.")
            return

        with open(files[0], encoding="utf-8") as f:
            snapshot = json.load(f)

        baseline = snapshot["value"]
        recent_trades = load_recent_trades()
        current_metrics = update_bot_stats(recent_trades, current_equity)
        current_value = current_metrics.get(metric_name.lower())

        if current_value is None:
            send_telegram_message(f"⚠️ Metrica `{metric_name}` non disponibile nei dati attuali.")
            return

        if metric_name == "MAX_ALLOWED_DRAWDOWN":
            improved = current_value < baseline
        else:
            improved = current_value >= baseline

        if improved:
            unlock_param(metric_name)
            send_telegram_message(f"✅ Patch su `{metric_name}` confermata: miglioramento da {baseline:.4f} → {current_value:.4f}")
        else:
            unlock_param(metric_name)
            if os.path.exists(LAST_PATCH_PATH):
                with open(LAST_PATCH_PATH, encoding="utf-8") as f:
                    original_patch = json.load(f)
                rollback_path = save_reverse_patch(original_patch)
                applied = apply_reverse_patch_file(rollback_path)
                if applied:
                    patch_id = get_latest_patch_id(metric_name)
                    mark_patch_status(patch_id, "rollback")
                    send_telegram_message(f"↩️ Patch rollbackata su `{metric_name}`: da {baseline:.4f} → {current_value:.4f}")
                else:
                    send_telegram_message(f"🚫 Rollback fallito su `{metric_name}`")
            else:
                send_telegram_message("⚠️ Nessuna patch originale trovata per rollback")

    except Exception as e:
        send_telegram_message(f"🚫 Errore in valutazione post-patch: {e}")

def save_patch_snapshot(metric_name: str, value: float):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{metric_name}.json"
    path = os.path.join(PATCH_SNAPSHOT_DIR, filename)
    data = {
        "timestamp": ts,
        "metric": metric_name,
        "value": value
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def detect_crash_file_flag():
    return os.path.exists("TRADING_BOT_CRASHED.flag")

def handle_crash_and_generate_patch(file_path: str, error: str, code: str = None):
    """
    Gestisce un crash del bot:
    - costruisce un fallback_context
    - genera una patch con GPT
    - delega l'applicazione a process_patch_file()
    """

    from openai_manager import generate_patch_from_context
    from .supervisor import process_patch_file

    print(f"[Supervisor] ⚠️ Crash rilevato in {file_path}. Avvio procedura GPT...")

    # Legge il codice se non fornito
    if code is None:
        try:
            with open(file_path, encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            send_telegram_message(f"❌ Impossibile leggere il file crashato: {file_path}\n{e}")
            return

    # Costruisce context fallback
    fallback_context = {
        "file": file_path,
        "code": code,
        "error": error,
        "fallback_mode": True
    }

    patch = generate_patch_from_context(fallback_context)

    if not patch or "modification" not in patch:
        send_telegram_message(f"❌ GPT non ha prodotto una patch valida per il crash in `{file_path}`.")
        return

    # Usa il ciclo completo blindato
    patched = process_patch_file(patch)

    if patched:
        send_telegram_message(f"✅ Patch generata e applicata con successo da crash handler.")
    else:
        send_telegram_message(f"❌ Patch da crash handler non applicata.")

def handle_perf_degradation(profit, precision, winrate, drawdown, failing_metrics: list):
    if not mgr_set.CALL_GPT_FOR_SUGGESTIONS:
        return

    # Check su parametri già sotto lock
    target_param = None
    if "low_winrate" in failing_metrics:
        target_param = "WINRATE"
    elif "low_profit" in failing_metrics:
        target_param = "DAILY_PROFIT_TARGET"
    elif "low_ev" in failing_metrics:
        target_param = "RITORNO_PER_TRADE"
    elif "high_drawdown" in failing_metrics:
        target_param = "MAX_ALLOWED_DRAWDOWN"
    elif "low_lstm_accuracy" in failing_metrics:
        target_param = "LSTM_ACCURACY"

    if target_param:
        metric_val_map = {
            "WINRATE": winrate,
            "DAILY_PROFIT_TARGET": profit,
            "RITORNO_PER_TRADE": profit / winrate if winrate else 0,
            "MAX_ALLOWED_DRAWDOWN": drawdown,
            "LSTM_ACCURACY": precision
        }
        current_value = metric_val_map.get(target_param, None)
    if current_value is not None:
        save_patch_snapshot(target_param, current_value)

    if target_param and is_param_locked(target_param):
        send_telegram_message(f"🔒 Patch su `{target_param}` già in test. Skippata richiesta GPT.")
        return

    context = generate_context_for_gpt() if mgr_set.CONTEXT_INCLUDE_CODE else ""

    prompt = f"""
📉 Il bot sta performando sotto target.

📊 Stato attuale:
- Profitto medio giornaliero: {profit*100:.2f}%
- Precisione segnali: {precision*100:.2f}%
- Winrate: {winrate*100:.2f}%
- Drawdown massimo: {drawdown*100:.2f}%
- Metriche critiche: {', '.join(failing_metrics)}

🎯 Obiettivi:
- DAILY_PROFIT_TARGET: {mgr_set.DAILY_PROFIT_TARGET}
- PRECISION_TARGET: {mgr_set.PRECISION_TARGET}
- DRAWDOWN massimo: {mgr_set.MAX_ALLOWED_DRAWDOWN}
- WINRATE minimo: {mgr_set.WINRATE}

Contesto tecnico:
{context}

Crea una patch correttiva specifica (parametri o codice). Rispetta la struttura JSON.
"""

    try:
        filename, suggestion = parse_and_save_suggestion(prompt)
        if suggestion:
            send_telegram_message(f"📩 Patch GPT generata da degradazione performance: `{filename}`")
            if mgr_set.FULL_PRODUCTION_MODE:
                integrate_modification()
                send_telegram_message("✅ Patch applicata automaticamente (produzione).")
            else:
                send_telegram_message("🛑 Patch in attesa di approvazione manuale.")
        else:
            send_telegram_message("⚠️ Nessuna patch valida generata da GPT.")
    except Exception as e:
        logging.error(f"[Supervisor] Errore GPT/Agent: {e}")
        send_telegram_message(f"⚠️ Errore durante generazione patch: {e}")

def check_performance(bot_stats: dict, model_accuracy: dict, market_state: dict) -> list[str]:
    triggers = []
    
    # winrate sotto la soglia indicata
    if bot_stats.get("winrate", mgr_set.WINRATE) < mgr_set.WINRATE:
        triggers.append("low_winrate")
    # drawdown massimo superato    
    if bot_stats.get("max_drawdown", mgr_set.MAX_ALLOWED_DRAWDOWN) > mgr_set.MAX_ALLOWED_DRAWDOWN:
        triggers.append("high_drawdown")
    # daily profit sotto soglia
    if bot_stats.get("daily_profit", mgr_set.DAILY_PROFIT_TARGET) < mgr_set.DAILY_PROFIT_TARGET:
        triggers.append("low_profit")
    # ritorno medio per trade sotto soglia
    if bot_stats.get("avg_trade_ev", mgr_set.RITORNO_PER_TRADE) < mgr_set.RITORNO_PER_TRADE:
        triggers.append("low_ev")
    # LSTM model non accurato
    if model_accuracy.get("lstm", mgr_set.LSTM_ACCURACY) < mgr_set.LSTM_ACCURACY:
        triggers.append("low_lstm_accuracy")    
    # precisione sotto soglia
    if bot_stats.get("precision", mgr_set.PRECISION_TARGET) < mgr_set.PRECISION_TARGET:
        triggers.append("low_precision")
    avg_vol = market_state.get("avg_volatility", 0.0)
    curr_vol = market_state.get("current_volatility", 0.0)
    # volatilità dei risultati dei modelli troppo alta, discostamento significativo dalla previsione attesa
    if abs(curr_vol - avg_vol) > 0.12:
        triggers.append("volatility_shift")

    return triggers
