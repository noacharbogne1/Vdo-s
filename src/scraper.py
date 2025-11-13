import utils_scraping
import config
import manage_db as db
import ocr

import sqlite3
from PyPDF2 import PdfReader
def test():

    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, file_name, path FROM files")
    pdfs = c.fetchall()

    total = len(pdfs)
    ok = 0
    failed = 0

    print(f"--- Test d'ouverture de {total} PDF ---")

    for i, (pdf_id, file_name, path) in enumerate(pdfs, start=1):
        try:
            reader = PdfReader(path)
            # Essai de lire la première page pour valider complètement
            _ = reader.pages[0]  
            ok += 1
            print(f"[{i}/{total}] ✅ OK : {file_name}")
        except Exception as e:
            failed += 1
            print(f"[{i}/{total}] ❌ ERREUR : {file_name} — {e}")

    print("\n--- Résultat final ---")
    print(f"PDF valides : {ok}/{total}")
    print(f"PDF corrompus/non lisibles : {failed}/{total}")

    conn.close()


def main():
    db.init_db()

    if config.DO_TEST_CODE:
        test()

    # 1) récupérer les JSON depuis la recherche Attrap via l'API
    if config.DO_GET_JSONS:
        utils_scraping.get_pdf_jsons()

    # 2) traiter les JSON téléchargés, enregistrement dans la db
    if config.DO_PROCESS_JSONS:
        utils_scraping.process_jsons()

    # 3) télécharger les PDF des arrêtés
    if config.DO_DOWNLOAD_PDFS:
        utils_scraping.download_pdfs()

    # 4) pour chaque PDF : extraire le texte et l'enregistrer dans la db
    if config.DO_EXTRACT_TEXT:
        ocr.extraction()

if __name__ == "__main__":
    main()
