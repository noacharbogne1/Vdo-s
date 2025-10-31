import os
import datetime
import time
import re
import random

import requests
import pandas as pd
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from urllib.parse import urljoin
import ocrmypdf
import sqlite3

import config
import manage_db as db

def is_pdf_link(href):
    """Retourne True si href semble pointer vers un PDF."""
    if not href:
        return False
    return href.lower().endswith(".pdf") or ".pdf" in href.lower()

def try_parse_year_month_from_string(str):
    """
    Tente d'extraire une année et un mois depuis une chaîne (nom de fichier, URL, titre).
    Retourne (année:int, mois:int) ou None si échec.
    On cherche des motif<s comme 2021-07, 202107, 2021_07, RAA2021-07, etc.
    """

    # regex pour extraire la première date au format JJ/MM/AAAA
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", str)
    if m:
        date_str = m.group(1)
        dt = datetime.datetime.strptime(date_str, "%d/%m/%Y")
        return dt.year, dt.month
    return None

def get_pdf_links(start_url):
    """
    1) Télécharge la page START_URL
    2) Récupère les liens vers les pages annuelles/mensuelles (liens qui contiennent RAA ou RAA-)
    3) Sur chaque page trouvée, récupère tous les liens .pdf (absolute URLs)
    Retourne une liste d'URLs absolues vers des PDF.
    """
    pdf_data = {}
    r = requests.get(start_url, headers=config.REQUEST_HEADERS)   # GET de la page principale
    r.raise_for_status()                          # lever une erreur si code HTTP != 200
    soup = BeautifulSoup(r.text, "html.parser")  # parser HTML avec BeautifulSoup

    # repérer d'abord les liens "années" / "RAA" — souvent le site liste les années ou les bulletins
    # ici on prend les <a> qui contiennent "RAA" dans le texte ou "RAA" dans l'href
    candidates = []
    for a in soup.find_all("a"):
        text = (a.get_text() or "").strip()
        href = a.get("href") or ""
        if "RAA" in text or "RAA" in href or "Recueil des actes administratifs" in text:
            # construire URL absolue et ajouter comme page candidate
            candidates.append(urljoin(config.BASE_URL, href))

    # dédupliquer et parcourir chaque page candidate (politesse : pause)
    candidates = list(dict.fromkeys(candidates))  # préserve l'ordre, supprime doublons
    for page_url in candidates:
        # parfois href vide ou ancre, skip
        if not page_url or page_url == "#":
            continue
        try:
            time.sleep(random.randint(1,3))      # pause pour ne pas spamer le serveur
            r2 = requests.get(page_url, headers=config.REQUEST_HEADERS)
            r2.raise_for_status()
            soup2 = BeautifulSoup(r2.text, "html.parser")
            # chercher tous les liens <a> qui semblent pointer sur des PDF
            for a in soup2.find_all("a"):
                text = (a.get_text() or "").strip()
                href = a.get("href") or ""
                if is_pdf_link(href):
                    full = urljoin(config.BASE_URL, href)  # construire url absolue
                    pdf_data[text] = full
        except Exception as e:
            # on attrape les exceptions pour ne pas arrêter tout le scraping si une page pose problème
            print(f"Warning: impossible d'ouvrir {page_url} — {e}")
            continue

    return pdf_data # retourne un dictionnaire avec une clé (texte) et une valeur (URL du pdf)

def filter_links_since(links, from_date):
    """
    Identifie la date de chaque PDF et conserve ceux ultérieurs à juillet 2020 dans kept
    Les PDF dont la date n'est pas identifiable sont mis de côté dans unknown
    """
    kept = []
    unknown = []
    for text, url in links.items():
        parsed = try_parse_year_month_from_string(text)
        if parsed:
            year, month = parsed
            if datetime.date(year, month, 1) >= from_date:
                kept.append((url, datetime.date(year, month, 1)))
        else:
            unknown.append(url)  # conserver les PDF dont la date n'a pas pu être identiée, pour l'instant on les garde de côté
    if unknown:
        print(f"{len(unknown)} liens n'ont pas de date identifiable depuis l'URL.")
    return kept  # liste de tuples (url, date)

def download_pdfs(url_date_pairs, dest_dir):
    """
    Télécharge chaque PDF (si pas déjà présent) et insère les métadonnées dans la table pdfs.
    url_date_pairs : liste de (url, date)
    """
    results = []
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()

    for url, dt in url_date_pairs:
        fname = os.path.basename(url.split("?")[0])  # nom de fichier sans query string
        local_path = os.path.join(dest_dir, fname)

        # si existe déjà, on skip le téléchargement mais on vérifie que déjà présent dans db
        if os.path.exists(local_path):
            print(f"Skipping (exists): {fname}")
            c.execute("""
                INSERT OR IGNORE INTO pdfs (file_name, url, date)
                VALUES (?, ?, ?)
            """, (fname, url, dt.isoformat()))
            conn.commit()
            results.append((url, dt, local_path))
            continue

        try:
            time.sleep(random.randint(1,3))
            r = requests.get(url, headers=config.REQUEST_HEADERS, stream=True, timeout=30)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"Téléchargé: {fname}")

            c.execute("""
                INSERT OR IGNORE INTO pdfs (file_name, url, date)
                VALUES (?, ?, ?)
            """, (fname, url, dt.isoformat()))
            conn.commit()

            results.append((url, dt, local_path))

        except Exception as e:
            print(f"Erreur téléchargement {url} : {e}")
            continue
    
    conn.close()
    return results  # liste de (url, date, local_path)

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
