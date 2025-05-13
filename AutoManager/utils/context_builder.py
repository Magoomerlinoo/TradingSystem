# Automanager/utils/context_builder.py

import os
import json
import re
import ast

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MOD_JSON_PATH = os.path.join(BASE_DIR, "modification_logs", "json")
SETTINGS_PATH = os.path.join(BASE_DIR, "..", "TradingBot", "settings.py")

def read_file_lines(filepath):
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.readlines()
    except Exception:
        return []

def is_ast_valid(code_str: str) -> bool:
    try:
        ast.parse(code_str)
        return True
    except:
        return False

def extract_code_snippet_with_lines(file_path, location_type, location_value):
    lines = read_file_lines(file_path)
    if not lines:
        return None

    match_index = None
    if location_type == "line":
        match_index = int(location_value) - 1
    elif location_type == "string":
        for i, line in enumerate(lines):
            if location_value in line:
                match_index = i
                break
    elif location_type == "regex":
        try:
            pattern = re.compile(location_value)
            for i, line in enumerate(lines):
                if pattern.search(line):
                    match_index = i
                    break
        except Exception:
            return None

    if match_index is None:
        return None

    start = max(0, match_index - 3)
    end = min(len(lines), match_index + 4)
    snippet = [f"[{i+1}] {lines[i].rstrip()}" for i in range(start, end)]
    return '\n'.join(snippet)

def extract_param_block(param_name):
    lines = read_file_lines(SETTINGS_PATH)
    for i, line in enumerate(lines):
        if line.strip().startswith(param_name):
            start = max(0, i - 2)
            end = min(len(lines), i + 2)
            snippet = [f"[{j+1}] {lines[j].rstrip()}" for j in range(start, end)]
            return '\n'.join(snippet)
    return None

def build_prompt_context():
    context = []

    for filename in os.listdir(MOD_JSON_PATH):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(MOD_JSON_PATH, filename)
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        ctx = f"\n--- CONTEXT FROM: {filename} ---\n"

        if data.get("modification_type") == "param_update":
            param = data.get("param_to_modify")
            snippet = extract_param_block(param)
            if snippet:
                ctx += f"[settings.py]\n{snippet}"

        elif data.get("modification_type") == "code_patch":
            rel_path = data.get("file")
            location = data.get("modification", {}).get("location", {})
            loc_type = location.get("type")
            loc_value = location.get("value")
            abs_path = os.path.join(BASE_DIR, "..", "TradingBot", rel_path)

            code = ''.join(read_file_lines(abs_path))
            if not is_ast_valid(code):
                print(f"[ContextBuilder] ⚠️ AST invalido per {rel_path}, salto.")
                continue

            snippet = extract_code_snippet_with_lines(abs_path, loc_type, loc_value)
            if snippet:
                ctx += f"[{rel_path}]\n{snippet}"

        context.append(ctx.strip())

    return "\n\n".join(context)

def get_module_role(file_path: str) -> str:
    """
    Ritorna una descrizione semantica del ruolo del file per GPT.
    """
    fname = os.path.basename(file_path).lower()
    if "bot.py" in fname:
        return "ciclo principale del trading bot"
    elif "supervisor" in fname:
        return "gestore patch e monitoraggio"
    elif "settings" in fname:
        return "file parametri dinamici"
    elif "watchdog" in fname:
        return "controllo stabilità e heartbeat"
    elif "manager" in fname or "controller" in fname:
        return "modulo di gestione o controllo logico"
    return "modulo secondario del bot"

def build_fallback_context(file_path: str, error: str) -> dict:
    """
    Costruisce un context GPT fallback completo per un file crashato.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            code = f.read()
    except Exception:
        return {}

    return {
        "file": file_path,
        "code": code,
        "error": error,
        "role": get_module_role(file_path),
        "fallback_mode": True
    }
