import datetime
import time
import random

BASE_URL = "https://www.val-de-marne.gouv.fr"    # base du site (utilisée pour urljoin)
START_URL = BASE_URL + "/Publications/Publications-legales/RAA-Recueil-des-actes-administratifs"
PDF_DIR = "/Users/noacharbogne/Documents/DataJ/Vidéo-surveillance/data/pdfs" # dossier où on sauvegarde les PDF
TEXT_DIR = "/Users/noacharbogne/Documents/DataJ/Vidéo-surveillance/data/texts" # dossier où on sauvegarde les textes extraits
FROM_DATE = datetime.date(2020, 7, 1)            # date minimale : juillet 2020 (inclus)
REQUEST_HEADERS = {"User-Agent": "RAA-Scraper/1.0 (+contact)"}  # header basique pour les requêtes
DB_PATH = "/Users/noacharbogne/Documents/DataJ/Vidéo-surveillance/data/raa.db"

# contrôle des différentes parties du code
DO_TEST_CODE = False
DO_SCRAPE_LINKS = False
DO_DOWNLOAD_PDFS = False
DO_EXTRACT_TEXT = True
DO_INTERPRET_TEXT = False