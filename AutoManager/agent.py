# AutoManager/agent.py

import os
import sys
import json
from AutoManager.json_schema import patch_schema
from datetime import datetime
from TradingBot import settings_manager as mgr_set
from AutoManager.openai_manager import ask_gpt_for_patch, SYSTEM_MSG
from AutoManager.integrator import MOD_JSON_PATH

def parse_and_save_suggestion(user_prompt: str):
    """
    1) Chiede a GPT (function-calling) di generare un JSON di patch
    2) Valida con jsonschema secondo patch_schema
    3) Salva il JSON in modification_logs/json/
    Ritorna (filename, suggestion_dict) oppure None se fallisce.
    """

    print("[Agent] Inizio richiesta GPT...")
    suggestion = ask_gpt_for_patch(user_prompt)

    print("[Agent] Risposta GPT:", suggestion)  # <== DEBUG
    # 🔒 Check pre-lock per patch già in testing
    if suggestion.get("file") and suggestion.get("modification"):
        rel_file = suggestion.get("file")
        loc_cfg  = suggestion.get("modification", {}).get("location", {})
        loc_val  = str(loc_cfg.get("value"))
        if is_file_location_locked(rel_file, loc_val):
            print(f"[Agent] ⚠️ Patch bloccata: {rel_file}::{loc_val} è in lock. Skip richiesta.")
            return None


    if not isinstance(suggestion, dict):
        print("[Agent] Risposta GPT non è un dict JSON.")
        return None

    # Validazione jsonschema
    try:
        jsonschema.validate(suggestion, patch_schema)
    except Exception as e:
        print(f"[Agent] JSON non valido: {e}")
        return None

    # 3) Salvataggio file
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}.json"
    filepath = os.path.join(MOD_JSON_PATH, filename)

    try:
        os.makedirs(MOD_JSON_PATH, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(suggestion, f, indent=2)
        print(f"[Agent] Suggerimento salvato: {filename}")
        return filename, suggestion
    except Exception as e:
        print(f"[Agent] Errore salvataggio JSON: {e}")
        return None