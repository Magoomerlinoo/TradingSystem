# utils/logger.py
import logging
import settings
import os

LOG_PATH = os.path.join(os.getcwd(), settings.LOG_FILE)  # e.g. "log.txt"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log_info(msg):
    logging.info(msg)
    print(msg)

def log_warning(msg):
    logging.warning(msg)
    print(f"WARNING: {msg}")

def log_error(msg):
    logging.error(msg)
    print(f"ERROR: {msg}")

def log_event(msg):  # Fallback alias
    log_info(msg)