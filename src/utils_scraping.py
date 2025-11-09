import os
import time
import random
import json
import math


import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

import config

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

def iter_json_files():
    """
    Renvoie les chemins des fichiers JSON du dossier.
    """
    for filename in os.listdir(config.JSON_DIR):
        if filename.endswith(".json") and not filename.startswith("."):
            yield os.path.join(config.JSON_DIR, filename)

def process_jsons():
    """
    Parcourt chaque JSON, extrait les métadonnées de chaque fichier RAA et les insère dans la table files.
    """
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()

    for filepath in iter_json_files():
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding='utf-8') as f:
            try:
                data = json.load(f)
                for element in data.get("elements", []):
                    name = element.get("name")
                    url = element.get("url")
                    date = element.get("date")
                    prefecture = element.get("administration")[4:]
                    if prefecture == "ris\0":
                        prefecture = "75"
                    c.execute("""
                        INSERT OR IGNORE INTO files (file_name, url, date, pref)
                        VALUES (?, ?, ?, ?)
                    """, (name, url, date, prefecture))
                    print(f"✅ Métadonnées extraites pour le JSON {filename}, fichier : {name}")
                    conn.commit()
            except Exception as e:
                print(f"⚠️ Erreur avec {filename} : {e}")
    
    conn.close()

def download_one(url, max_retries=3):
    """
    Télécharge un PDF à partir d'un URL
    """
    header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
    if not url:
        print("URL vide")
        return
    filename = os.path.basename(urlparse(url).path)
    if not filename:
        "fichier_sans_nom.bin"
    filepath = os.path.join(config.PDF_DIR, filename)
    if os.path.exists(filepath):
        print(f"✅ Fichier déjà présent : {filename}")
        return
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, stream=True, timeout=(10, 30), headers=header)
            r.raise_for_status()
            with open(os.path.join(filepath), 'wb') as outfile:
                outfile.write(r.content)
            time.sleep(random.randint(1,3))
            print(f"✅ Téléchargé : {filename}")
            return
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Erreur ({e.__class__.__name__}) sur {filename}: {e}", flush=True)
            if attempt < max_retries:
                wait = 3 * attempt
                print(f"Nouvelle tentative dans {wait}s...", flush=True)
                time.sleep(wait)
            else:
                print(f"❌ Échec final pour {url}", flush=True)
                with open("failed_downloads.txt", "a", encoding="utf-8") as log:
                    log.write(url + "\n\n")

def download_pdfs(max_workers=1):
    """
    Parcourt la db et accède à l'URL de chaque RAA extrait.
    Télécharge chaque RAA (si pas déjà présent)
    """
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    urls = [row[0] for row in c.execute("SELECT url FROM files WHERE url IS NOT NULL")]
    conn.close()

    for i, url in enumerate(urls, 1):
        print(f"➡️ Fichier n°{i} sur {len(urls)} fichiers")
        download_one(url)
