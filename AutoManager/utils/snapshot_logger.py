#snapshot_logger.py

import os
import json
from datetime import datetime
from AutoManager.utils.patch_logger_sql import init_db, log_patch

PATCH_SNAPSHOT_DIR = "modification_logs/snapshots"

# Inizializza il database al primo import
init_db()

def save_metric_snapshot(metric_name: str, value: float) -> str:
    """
    Salva uno snapshot della metrica in formato JSON.
    """
    os.makedirs(PATCH_SNAPSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{metric_name.upper()}.json"
    filepath = os.path.join(PATCH_SNAPSHOT_DIR, filename)

    snapshot = {
        "timestamp": timestamp,
        "metric": metric_name.upper(),
        "value": round(value, 6)
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    return filepath
