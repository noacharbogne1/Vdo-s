import os

import tempfile
import ocrmypdf
import sqlite3

from concurrent.futures import ProcessPoolExecutor, as_completed
from pdfminer.high_level import extract_text
from urllib.parse import quote
import ocrmypdf
import sqlite3
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, NumberObject
import ftfy
import shutil

import config
import manage_db as db

def flatten_pdf(input_path, output_path):
    """
    Supprime les formulaires / annotations d'un PDF pour le rendre OCRisable.
    """
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        for page in reader.pages:
            if page.get("/Annots"):
                for annot in page.get("/Annots"):
                    annot_obj = annot.get_object()
                    annot_obj.update({NameObject("/Ff"): NumberObject(1)})
            writer.add_page(page)

        writer.write(output_path)
        writer.close()
        return True
    except Exception as e:
        print(f"⚠️ Erreur flatten sur {input_path}: {e}")
        return False

def extract_text_from_pdf(fname, pdf_path):
    """
    Effectue un OCR sur un PDF, puis extrait le texte.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_flat:
        flat_path = tmp_flat.name
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_ocr:
        ocr_path = tmp_ocr.name

    try:
        if not flatten_pdf(pdf_path, flat_path):
            print(f"⚠️ Flatten échoué pour {fname}, OCR direct.")
            flat_path = pdf_path

        print(f"➡️ OCR en cours pour {fname}")
        ocrmypdf.ocr(
            flat_path,
            ocr_path,
            language="fra+eng",
            redo_ocr=True,            # OCR aussi sur pages mixtes
            skip_big=250,             # saute pages > 250 Mpix
            max_image_mpixels=250,    # évite decompression bomb
            optimize=0,               # pas de recompression
            invalidate_digital_signatures=True,
            progress_bar=False,
            quiet=True,
            jobs=1
        )

        reader = PdfReader(ocr_path)
        ftfy_config = ftfy.TextFixerConfig(unescape_html=False, explain=False)
        pages = []

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            fixed_text = ftfy.fix_text(page_text, config=ftfy_config)
            pages.append({"page": i + 1, "text": fixed_text.strip()})

    except Exception as e:
        print(f"⚠️ OCR échoué pour {fname}: {e}")
        text = ""
    finally:
        for path in [flat_path, ocr_path]:
            if os.path.exists(path):
                os.remove(path)

    return pages

def process_one_pdf(pdf):
    """
    Fonction exécutée pour chaque processus.
    """
    pdf_id, file_name, path = pdf
    if not os.path.exists(path):
        print(f"⚠️ PDF {file_name} introuvable — ignoré.")
        return (pdf_id, file_name, [], False)

    try:
        pages = extract_text_from_pdf(file_name, path)
        return (pdf_id, file_name, pages, True)
    except Exception as e:
        print(f"❌ Erreur sur {file_name}: {e}")
        return (pdf_id, file_name, [], False)

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

    c.execute("SELECT id, file_name, path FROM files WHERE ocr_done = 0")
    pdfs = c.fetchall()
    total = len(pdfs)
    done = 0

    for pdf in pdfs:
        pdf_id, file_name, path = pdf
        pdf_id, file_name, pages, success = process_one_pdf(pdf)
        done += 1

        if success:
            c.execute("BEGIN TRANSACTION")
            for page in pages:
                db.insert_page(pdf_id, page["page"], page["text"])
            c.execute("COMMIT")

            c.execute("UPDATE files SET ocr_done = 1 WHERE id = ?", (pdf_id,))
            conn.commit()

            print(f"[{done}/{total}] ✅ {file_name} ({len(pages)} pages)")
        else:
            print(f"[{done}/{total}] ⚠️ {file_name} échoué ou ignoré")

    conn.close()

