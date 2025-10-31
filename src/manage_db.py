import sqlite3
import os

import config

def init_db():
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS pdfs (
        id INTEGER PRIMARY KEY,
        file_name TEXT UNIQUE,
        url TEXT,
        date TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS pages (
        id INTEGER PRIMARY KEY,
        pdf_id INTEGER,
        page_number INTEGER,
        text TEXT,
        FOREIGN KEY(pdf_id) REFERENCES pdfs(id)
    )
    """)
    conn.commit()
    conn.close()

def get_pdf_id_by_filename(filename):
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id FROM pdfs WHERE file_name = ?", (filename,))
    result = c.fetchone()
    conn.close()

    return result[0] if result else None

def insert_page(pdf_id, page_number, text):
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO pages (pdf_id, page_number, text)
        VALUES (?, ?, ?)
    """, (pdf_id, page_number, text))
    conn.commit()
    conn.close()
