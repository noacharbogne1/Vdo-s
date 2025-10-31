import os
import datetime
import time
import re
import random
import json
import math

import requests
import pandas as pd
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import ocrmypdf
import sqlite3

import config
import manage_db as db

def fetch_page(page):
    """
    Télécharge une page JSON via l'API d'Attrap et l'enregistre localement.
    """
    try:
        url = config.URL_API.format(config.SEARCH, page)
        response = requests.get(url, headers=config.HEADERS)
        response.raise_for_status()
        data = response.json()
        
        filepath = os.path.join(config.JSON_DIR + f"attrap_page_{page}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        time.sleep(random.randint(1,3))
        return f"✅ Page {page} enregistrée"
    
    except Exception as e:
        return f"⚠️ Erreur page {page} : {e}"

def get_pdf_jsons(max_workers=3):
    """
    Enregistre les json de chaque page de la recherche effectuée via l'API d'Attrap.
    """
    page = 1
    response = requests.get(config.URL_API.format(config.SEARCH, page), headers=config.HEADERS)
    data = response.json()
    total_pages = math.ceil(data['total'] / 10)
    print(f"Total des pages pour la recherche Attrap : {total_pages}")

    with open(config.JSON_DIR + f"attrap_page_{page}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    pages = range(2, total_pages + 1)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_page, p) for p in pages]
        for i, future in enumerate(as_completed(futures), 1):
            print(f"[{i}/{len(pages)}] {future.result()}")

def process_jsons():
    """
    Parcourt chaque JSON, extrait les métadonnées de chaque fichier RAA et les insère dans la table files.
    """
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    
    list_url = []

    for filename in os.listdir(config.JSON_DIR):
        if filename.endswith(".json") and not filename.startswith("."):
            yield os.path.join(config.JSON_DIR, filename)

    for filepath in download_pdfs():
        with open(filepath, "r", encoding='utf-8') as f:
            try:
                data = json.load(f)
                for element in data.get("elements", []):
                    url = element.get("url")
                    date = element.get("date")
                    prefecture = element.get("administration")
                    c.execute("""
                        INSERT OR IGNORE INTO files (fichier, url, date, prefecture)
                        VALUES (?, ?, ?, ?)
                    """, (os.path.basename(filepath), url, date, prefecture))
            except Exception as e:
                print(f"⚠️ Erreur avec {filepath} : {e}")
    
    conn.commit()
    conn.close()

def download_one(url):
    """
    Télécharge un PDF à partir d'un URL
    """
    if not url:
        return "URL vide"
    filename = os.path.basename(urlparse(url).path)
    if not filename:
        "fichier_sans_nom.bin"
    filepath = os.path.join(config.PDF_DIR, filename)
    if os.path.exists(filepath):
        return f"Fichier déjà présent : {filename}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(r.content)
        time.sleep(random.randint(1,3))
        return f"✅ Téléchargé : {filename}"
    except Exception as e:
        return f"⚠️ Erreur : {url} → {e}"

def download_pdfs(max_workers=8):
    """
    Parcourt la db et accède à l'URL de chaque RAA extrait.
    Télécharge chaque RAA (si pas déjà présent)
    """
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    urls = [row[0] for row in c.execute("SELECT url FROM files WHERE url IS NOT NULL")]
    conn.close()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_one, url) for url in urls]
        for i, future in enumerate(as_completed(futures), 1):
            print(f"[{i}/{len(urls)}] {future.result()}")

    conn.close()

def extract_text_from_pdf(fname, pdf_path):
    """
    Page par page, tente d'extraire le texte du PDF en testant avec technique OCR

    Retourne: pages_text (list[dict]) : liste des pages sous la forme [{'page': n, 'text': '...'}]
    """
    output_path = "Users/noacharbogne/Documents/DataJ/Vidéo-surveillance/data/tmp/" + fname
    ocrmypdf.ocr(
        pdf_path,
        output_path,
        language="fra",
        skip_text=True,
        progress_bar=False
    )

    reader = PdfReader(output_path)
    pages_text = []
    for i, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages_text.append({"page": i, "text": page_text.strip()})
    
    return pages_text

def extraction():
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, file_name FROM pdfs")
    pdfs = c.fetchall()
    print("here\n")
    for pdf_id, fname in pdfs:
        local_path = os.path.join(config.PDF_DIR, fname)
        if not os.path.exists(local_path):
            print(f"⚠️ PDF {fname} introuvable dans la base — ignoré.")
            continue
        print(f"Extraction du texte : {fname}")
        pages = extract_text_from_pdf(fname, local_path)
        for page in pages:
            db.insert_page(pdf_id, page["page"], page["text"])
        print(f"✅ {len(pages)} pages insérées pour {fname}")

    conn.close()
