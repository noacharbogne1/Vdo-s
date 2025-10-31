import os

import sqlite3
import pandas as pd

import utils_scraping
import utils_interpreter
import config
import manage_db as db

def test():
    tests = ["Arrêté n°2024-123",
    "ARRETE 2020-01",
    "arrêté 2021-456",
    "Arrete n2022-789",
    "Arrêté interprefectoral N°2025 / 33",
    "A R R E T E "
]

def main():
    db.init_db()

    if config.DO_TEST_CODE:
        test()

    # 1) récupérer les liens PDF depuis la page RAA
    if config.DO_SCRAPE_LINKS:
        print("Récupération des liens PDF depuis la page RAA...")
        pdf_links = utils_scraping.get_pdf_links(config.START_URL)  # liste d'URLs
        print(f"{len(pdf_links)} PDF trouvés sur le site (brut).")

    # 2) filtrer ceux >= juillet 2020
        print(f"Filtrage des PDF depuis {config.FROM_DATE.isoformat()}...")
        url_date = utils_scraping.filter_links_since(pdf_links, config.FROM_DATE)  # liste de (url, date)
        print(f"{len(url_date)} PDF identifiés à partir de la date demandée.")

    # 3) télécharger les PDF filtrés
    if config.DO_DOWNLOAD_PDFS:
        print("Téléchargement des PDF...")
        utils_scraping.download_pdfs(url_date, config.PDF_DIR)

    # 4) pour chaque PDF : extraire le texte et l'enregistrer dans la db
    if config.DO_EXTRACT_TEXT:
        utils_scraping.extraction()
        #segments = utils.split_arretes(pages)

    # 5) pour chaque page : tester la présence de "vidéo-protection"
    if config.DO_INTERPRET_TEXT:
        utils_interpreter.interprete()

    # 6) exporter les résultats en CSV pour consultation
    # if config.DO_INTERPRET_TEXT:
    #     df = pd.DataFrame(records)
    #     out_csv = "raa_video_protection_results.csv"
    #     df.to_csv(out_csv, index=False, encoding="utf-8")
    #     print(f"Terminé — résultats sauvegardés dans {out_csv} ({len(df)} segments).")

if __name__ == "__main__":
    main()
