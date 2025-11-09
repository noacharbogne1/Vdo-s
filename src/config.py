import datetime
import time

# configuration de l'API
URL_API = "https://attrap.fr/api/v1/search?s={}&page={}&start_date=2020-07-01&end_date=2025-10-31&sort=desc"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
}
SEARCH = "vidéosurveillance+OR+%22vidéo-surveillance%22+OR+vidéoprotection+OR+%22vidéo-protection%22+OR+caméra&administration=ppparis,pref75,pref77,pref78,pref91,pref92,pref93,pref94,pref95"

# chemin des dossiers data
JSON_DIR = "/Users/noacharbogne/Documents/DataJ/Vidéo-surveillance/data/jsons/"
PDF_DIR = "/Users/noacharbogne/Documents/DataJ/Vidéo-surveillance/data/pdfs/" 
TEXT_DIR = "/Users/noacharbogne/Documents/DataJ/Vidéo-surveillance/data/texts/"
DB_PATH = "/Users/noacharbogne/Documents/DataJ/Vidéo-surveillance/data/raa.db"

# contrôle des différentes parties de la main
DO_TEST_CODE = False
DO_GET_JSONS = False
DO_PROCESS_JSONS = False
DO_DOWNLOAD_PDFS = False
DO_EXTRACT_TEXT = True
DO_INTERPRET_TEXT = False
