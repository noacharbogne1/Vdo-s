import sqlite3

import config
import manage_db

def interpreter():
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()

    