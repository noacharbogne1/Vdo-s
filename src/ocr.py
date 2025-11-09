import os

import tempfile
import ocrmypdf
import sqlite3

from concurrent.futures import ProcessPoolExecutor, as_completed
from pdfminer.high_level import extract_text
from urllib.parse import quote
import ocrmypdf
import sqlite3

import config
import manage_db as db

def extract_text_from_pdf(fname, pdf_path):
    """
    Effectue un OCR sur un PDF, puis extrait le texte.
    """

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

    try:
        ocrmypdf.ocr(
            pdf_path,
            tmp_path,
            language="fra",
            skip_text=False,
            force_ocr=True,
            deskew=True,
            optimize=1,
            progress_bar=False,
            quiet=True,
            jobs=1
        )

        # Extraction du texte OCRisé
        text = extract_text(tmp_path)

    except Exception as e:
        print(f"⚠️ OCR échoué pour {fname}: {e}")
        text = ""
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    pages = [{"page": i + 1, "text": p.strip()} for i, p in enumerate(text.split("\f"))]
    return pages

def process_one_pdf(pdf):
    """
    Fonction exécutée pour chaque processus.
    """
    pdf_id, file_name = pdf
    local_path = os.path.join(config.PDF_DIR, file_name)
    fname = file_name

    if not os.path.exists(local_path):
        encoded_name = quote(file_name)
        encoded_path = os.path.join(config.PDF_DIR, encoded_name)
        if os.path.exists(encoded_path):
            local_path = encoded_path
            fname = encoded_name
        elif os.path.exists(encoded_path + '.pdf'):
            local_path = encoded_path + '.pdf'
            fname = encoded_name + '.pdf'
        else:
            print(f"⚠️ PDF {file_name} introuvable — ignoré.")
            return (pdf_id, file_name, 0, False)

    try:
        pages = extract_text_from_pdf(fname, local_path)
        for page in pages:
            db.insert_page(pdf_id, page["page"], page["text"])
        print(f"✅ {len(pages)} pages insérées pour {file_name}")
        return (pdf_id, file_name, len(pages), True)
    except Exception as e:
        print(f"❌ Erreur sur {file_name}: {e}")
        return (pdf_id, file_name, 0, False)

def extraction():
    """
    Exécution en parallèle du traitement OCR des PDF.
    """
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()

    try:
        c.execute("ALTER TABLE files ADD COLUMN ocr_done INTEGER DEFAULT 0;")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    c.execute("SELECT id, file_name FROM files WHERE ocr_done = 0")
    pdfs = c.fetchall()

    cpu_total = os.cpu_count()
    max_workers = max(1, cpu_total - 2)
    print(f"Utilisation {max_workers} processeurs pour l'OCR des PDF")
    total = len(pdfs)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_one_pdf, pdf): pdf for pdf in pdfs}
        done = 0
        for future in as_completed(futures):
            pdf_id, file_name, nb_pages, success = future.result()
            done += 1
            if success:
                print(f"[{done}/{total}] ✅ {file_name} ({nb_pages} pages)")
                c.execute("UPDATE files SET ocr_done = 1 WHERE id = ?", (pdf_id,))
                conn.commit()
            else:
                print(f"[{done}/{total}] ⚠️ {file_name} échoué ou ignoré")

    conn.close()
