import sqlite3
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "../data/bot_data.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS patches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            file TEXT,
            metric TEXT,
            patch_json TEXT,
            reverse_json TEXT,
            status TEXT
        );
        CREATE TABLE IF NOT EXISTS performance_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            metric TEXT,
            value REAL
        );
        """)
        conn.commit()

def log_patch(file: str, metric: str, patch: dict, reverse: dict, status: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO patches (timestamp, file, metric, patch_json, reverse_json, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ts, file, metric, json.dumps(patch), json.dumps(reverse), status))
        conn.commit()

def mark_patch_status(patch_id: int, status: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE patches SET status = ? WHERE id = ?", (status, patch_id))
        conn.commit()

def log_snapshot(metric: str, value: float):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO performance_snapshot (timestamp, metric, value)
            VALUES (?, ?, ?)
        """, (ts, metric, value))
        conn.commit()

def get_latest_patch_id(metric_name: str) -> int | None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM patches
            WHERE metric = ?
            AND status = 'success'
            ORDER BY id DESC
            LIMIT 1
        """, (metric_name,))
        row = cur.fetchone()
        return row[0] if row else None

# Inizializza il DB al primo import
init_db()
