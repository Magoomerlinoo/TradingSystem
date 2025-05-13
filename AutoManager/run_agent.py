# run_agent.py
from agent import parse_and_save_suggestion

if __name__ == "__main__":
    prompt = """
    Modifica MIN_LOT_SIZE in settings.py da 0.01 a 0.05
    per test sulla liquidità giornaliera.
    Rispondi SOLO con il JSON di patch, senza testo libero.
    """
    filename, suggestion = parse_and_save_suggestion(prompt)
    print(f"✅ JSON salvato in: {filename}")
    print(suggestion)
