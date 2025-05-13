# patch_batc_manager.py

import os
import json
from collections import defaultdict
from lock_manager import is_param_locked
from integrator import apply_code_patch, absolute_bot_file
from validator import validate_python_file
from telegram_notifier import send_telegram_message
from patch_logger_sql import log_patch
from integrator_patch_utils import create_reverse_patch
from settings_manager import AUTO_APPLY_PATCHES

MOD_JSON_PATH = "modification_logs/"
PROCESSED_JSON_PATH = "modification_logs/processed/"

PRIORITY_ORDER = {
    "WINRATE": 1,
    "MAX_DRAWDOWN": 2,
    "DAILY_PROFIT": 3,
    "PRECISION": 4,
    "AVG_TRADE_EV": 5
}

def load_all_patches():
    patches = []
    for fn in os.listdir(MOD_JSON_PATH):
        if fn.endswith(".json"):
            with open(os.path.join(MOD_JSON_PATH, fn), encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    patches.append((fn, data))
                except Exception as e:
                    print(f"Errore lettura {fn}: {e}")
    return patches

def group_by_metric(patches):
    grouped = defaultdict(list)
    for name, patch in patches:
        metric = patch.get("metric", "UNDEFINED").upper()
        grouped[metric].append((name, patch))
    return grouped

def prioritize(grouped):
    return sorted(
        grouped.items(),
        key=lambda x: PRIORITY_ORDER.get(x[0], 99)
    )

def apply_batch_patches(current_equity):
    patches = load_all_patches()
    grouped = group_by_metric(patches)
    prioritized = prioritize(grouped)

    for metric, patch_group in prioritized:
        if is_param_locked(metric):
            continue

        json_name, patch = patch_group[0]
        print(f"[BatchManager] Provo patch: {json_name} su metrica {metric}")

        ok, loc, old, new, loc_type = apply_code_patch(patch, current_equity=current_equity)
        rel_file = patch.get("file")
        abs_file = absolute_bot_file(rel_file)

        if ok and validate_python_file(abs_file):
            reverse = create_reverse_patch(patch)
            log_patch(
                file=rel_file,
                metric=metric,
                patch=patch,
                reverse=reverse,
                status="success"
            )
            send_telegram_message(f"✅ Patch `{json_name}` applicata (metrica {metric})")
        else:
            send_telegram_message(f"🚫 Patch `{json_name}` fallita (metrica {metric})")

        try:
            os.rename(os.path.join(MOD_JSON_PATH, json_name), os.path.join(PROCESSED_JSON_PATH, json_name))
        except Exception as e:
            print(f"Errore spostamento {json_name}: {e}")
