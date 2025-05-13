import os
import json
from AutoManager.openai_manager import generate_patch_from_context
from AutoManager.integrator import apply_code_patch

# Percorso del file corrotto
FILE_PATH = "TradingSystem/TradingBot/bot.py"
ABS_PATH = os.path.abspath(FILE_PATH)

# 1. Carica contenuto originale
try:
    with open(ABS_PATH, encoding="utf-8") as f:
        code = f.read()
except FileNotFoundError:
    print(f"❌ File non trovato: {ABS_PATH}")
    exit(1)

# 2. Costruisce il contesto fallback
fallback_context = {
    "file": FILE_PATH,
    "code": code,
    "error": "SyntaxError: parsing fallito in ast.parse",
    "fallback_mode": True
}

print("\n[TEST] Invio fallback context a GPT...\n")

# 3. Richiede la patch a GPT
patch = generate_patch_from_context(fallback_context)

# 4. Verifica se patch è valida
if not isinstance(patch, dict) or "modification" not in patch:
    print("❌ Risposta GPT non valida o non formattata.")
    print(json.dumps(patch, indent=2))
    exit(1)

print("[PATCH RECEIVED]:\n", json.dumps(patch, indent=2))

# 5. Applica la patch
print("\n[APPLYING PATCH]...\n")
success, loc, old, new, typ = apply_code_patch(patch)

# 6. Esito finale
if success:
    print("✅ PATCH APPLICATA CON SUCCESSO")
    print(f"- Tipo: {typ}")
    print(f"- Target: {FILE_PATH}")
else:
    print("❌ PATCH FALLITA")
    print(f"- Motivo: {typ}")
    if old or new:
        print(f"- Old: {old}\n- New: {new}")
