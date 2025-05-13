# github_uploader.py

import subprocess
import os
from datetime import datetime
from . import settings_manager as mgr_set

# Percorso alla root della repo AutoManager
GIT_REPO_PATH = os.path.dirname(__file__)
# Branch configurabile in settings_manager
GIT_BRANCH = getattr(mgr_set, "GIT_BRANCH", "master")


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def git_add_commit_push():
    """
    Esegue git add, commit e push in modo automatico.
    Include tutte le modifiche a:
      - codice fonte (AutoManager)
      - log di integrazione (integration_logs/)
      - suggerimenti (modification_logs/)
      - eventuali patch al TradingBot (TradingBot/)
    """
    try:
        print("[GitHubUploader] Inizio upload automatico...")
        # Passa alla directory della repo
        os.chdir(GIT_REPO_PATH)

        # Aggiungi tutte le modifiche rilevanti
        subprocess.run(["git", "add", "-A"], check=True)
        print("[GitHubUploader] git add -A eseguito.")

        # Crea il messaggio di commit includendo timestamp
        ts = get_timestamp()
        commit_msg = f"Auto-patch: aggiornamento integrato il {ts}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        print(f"[GitHubUploader] git commit eseguito: '{commit_msg}'")

        # Pusha sul branch configurato
        subprocess.run(["git", "push", "origin", GIT_BRANCH], check=True)
        print(f"[GitHubUploader] git push completato sul branch '{GIT_BRANCH}'!")

    except subprocess.CalledProcessError as e:
        print(f"[GitHubUploader] Errore Git (CalledProcessError): {e}")
    except Exception as ex:
        print(f"[GitHubUploader] Errore inaspettato: {ex}")