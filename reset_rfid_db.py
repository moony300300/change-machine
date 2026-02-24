#!/usr/bin/env python3

import sqlite3
from databases.bank import BankDB

DB_PATH = "databases/bank.db"  # Adjust if your database is elsewhere

def reset_rfid_cards():
    print("[INFO] Resetting RFID card database...")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Drop the table if it exists
    c.execute("DROP TABLE IF EXISTS rfid_cards")
    print("[INFO] Dropped existing rfid_cards table.")

    # Recreate the table
    c.execute("""
        CREATE TABLE IF NOT EXISTS rfid_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid TEXT UNIQUE NOT NULL,
            value REAL NOT NULL,
            active INTEGER DEFAULT 0,
            isAdminKey BOOL DEFAULT 0
        )
    """)
    print("[INFO] Created new rfid_cards table.")
    
    conn.commit()
    conn.close()
    print("[INFO] RFID database reset complete.")


if __name__ == "__main__":
    reset_rfid_cards()
