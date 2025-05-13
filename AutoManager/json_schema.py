# json_schema.py
# Schema JSON per la function-calling delle patch (param_update e code_patch)
patch_schema = {
    "type": "object",
    "properties": {
        # Tipo di modifica: aggiornamento parametri o patch di codice
        "modification_type": {
            "type": "string",
            "enum": ["param_update", "code_patch"]
        },
        # Motore GPT suggerito
        "engine_used": {"type": "string"},
        # Specifico per param_update
        "param_to_modify": {"type": "string"},
        "new_value": {},
        "target_file": {"type": "string"},
        # Specifico per code_patch
        "file": {"type": "string"},
        "modification": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["replace", "insert", "delete"]
                },
                "location": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["string", "line", "regex"]
                        },
                        "value": {"type": "string"}
                    },
                    "required": ["type", "value"]
                },
                "old_value": {"type": "string"},
                "new_value": {}
            },
            "required": ["action", "location"]
        },
        # Metodo o funzione target (opzionale)
        "target_method": {"type": "string"},
        # Motivazione tecnica dettagliata
        "reason": {"type": "string"}
    },
    "required": ["modification_type", "reason"]
}