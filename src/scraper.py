import utils_scraping
import config
import manage_db as db
import ocr

def test():
    from pypdf import PdfReader

    try:
        reader = PdfReader("/Users/noacharbogne/Documents/DataJ/Vidéo-surveillance/data/pdfs/recueil-78-2024-100-recueil-des-actes-administratifs.pdf")
        print(f"{len(reader.pages)} pages détectées")
    except Exception as e:
        print(f"Erreur de lecture PDF : {e}")


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
