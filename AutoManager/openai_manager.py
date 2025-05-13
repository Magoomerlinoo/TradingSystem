#openai_manager.py

import json
import os
from openai import OpenAI
from AutoManager import settings_manager as mgr_set
from AutoManager.json_schema import patch_schema
from utils.context_builder import build_fallback_context


PATCH_FUNCTION_NAME = "propose_patch"
client = OpenAI(api_key=mgr_set.OPENAI_API_KEY)

SYSTEM_MSG = """
⚠️ RISPOSTA VINCOLATA A JSON

Sei un assistente tecnico integrato in un sistema di patching automatizzato per un bot di trading.
Il tuo unico compito è generare patch correttive in formato JSON, nel rispetto totale dello schema previsto (param_update o code_patch).

NON devi scrivere testo, commenti, spiegazioni o output extra. SOLO ed ESCLUSIVAMENTE un oggetto JSON conforme.
"""

def build_fallback_prompt(context: dict) -> str:
    file = context.get("file")
    code = context.get("code", "")
    error = context.get("error", "Errore non specificato")

    base_name = os.path.basename(file)
    module_role = "modulo secondario"
    if "bot.py" in file:
        module_role = "ciclo principale del trading bot"
    elif "supervisor" in file:
        module_role = "gestore patch e monitoraggio"
    elif "settings" in file:
        module_role = "file parametri dinamici"
    elif "manager" in file or "controller" in file:
        module_role = "componente di controllo o gestione"

    return f"""
Hai ricevuto un file Python danneggiato proveniente dal sistema automatico di patching di un bot di trading.

🔧 Obiettivo: correggi il file mantenendo la sua logica, struttura e funzionalità.

📄 File: {file}
🧠 Ruolo: {module_role}
🚫 Errore: {error}

--- INIZIO FILE ---
{code}
--- FINE FILE ---

✅ Restituisci solo questo oggetto JSON:

{{
  "file": "{file}",
  "modification_type": "code_patch",
  "engine_used": "gpt-4-turbo",
  "modification": {{
    "action": "replace",
    "location": {{ "type": "full_file", "value": "" }},
    "new_value": "NUOVO CODICE QUI"
  }},
  "reason": "Correzione automatica da fallback mode"
}}
""".strip()

def generate_patch_from_context(context: dict) -> dict:
    fallback_mode = context.get("fallback_mode", False)

    # Auto-costruzione fallback context se manca il prompt
    if fallback_mode and ("prompt" not in context or not context["prompt"]):
        context = build_fallback_context(context)

    if fallback_mode:
        prompt = build_fallback_prompt(context)
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            return {"error": f"[FallbackGPT] Errore parsing risposta: {e}"}

    else:
        code = context.get("code", "")
        state = context.get("state", "")
        metrics = context.get("metrics", "")
        prompt = f"""
Sistema operativo del bot. Correggi o migliora il seguente codice Python in base allo stato e metrica.

CODICE:
{code}

STATO:
{state}

METRICHE:
{metrics}
"""
        return ask_gpt_for_patch(prompt)

def ask_gpt_for_patch(prompt: str) -> dict:
    functions = [{
        "name": PATCH_FUNCTION_NAME,
        "description": "Genera un JSON di patch per il codice o parametri",
        "parameters": patch_schema
    }]
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user",   "content": prompt}
        ],
        functions=functions,
        function_call={"name": PATCH_FUNCTION_NAME}
    )
    msg = response.choices[0].message
    func = getattr(msg, "function_call", None)
    if func is None:
        raise RuntimeError("Nessuna function_call nella risposta di GPT")

    raw = getattr(func, "arguments", None) or (func["arguments"] if isinstance(func, dict) else None)
    try:
        print("[OpenAI Manager] JSON ricevuto:\n", raw)
        return json.loads(raw)
    except Exception as e:
        raise ValueError(f"Impossibile decodificare gli arguments JSON: {e}")

def web_search(prompt: str) -> str:
    return "[WebSearch] Non implementato."

def ask_gpt(prompt: str, engine_hint: str = None, functions: list = None) -> str:
    try:
        if engine_hint == "browser":
            return web_search(prompt)

        if engine_hint == "codex":
            resp = client.completions.create(
                model="code-davinci-002",
                prompt=prompt,
                max_tokens=1500,
                temperature=0.2
            )
            return resp.choices[0].text.strip()

        if engine_hint == "function_call":
            resp = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "Sei un assistente tecnico specializzato."},
                    {"role": "user",   "content": prompt}
                ],
                functions=functions or [],
                function_call="auto"
            )
            return resp.choices[0].message.content or resp.choices[0].message

        resp = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Sei un assistente per il miglioramento di bot di trading."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        print(f"[OpenAI Manager] Errore durante chiamata GPT: {e}")
        return None