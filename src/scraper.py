import utils_scraping
import config
import manage_db as db
import ocr

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

    # 1) récupérer les JSON depuis la recherche Attrap via l'API
    if config.DO_GET_JSONS:
        print("Récupération des json depuis l'API Attrap...")
        utils_scraping.get_pdf_jsons()

    # 2) traiter les JSON téléchargés, enregistrement dans la db
    if config.DO_PROCESS_JSONS:
        print("Traitement des JSONS...")
        utils_scraping.process_jsons()

    # 3) télécharger les PDF des arrêtés
    if config.DO_DOWNLOAD_PDFS:
        print("Téléchargement des PDF...")
        utils_scraping.download_pdfs()

    # 4) pour chaque PDF : extraire le texte et l'enregistrer dans la db
    if config.DO_EXTRACT_TEXT:
        ocr.extraction()

    # 5) pour chaque page : tester la présence de "vidéo-protection"
    # if config.DO_INTERPRET_TEXT:
        # utils_interpreter.interprete()

    # 6) exporter les résultats en CSV pour consultation
    # if config.DO_INTERPRET_TEXT:
    #     df = pd.DataFrame(records)
    #     out_csv = "raa_video_protection_results.csv"
    #     df.to_csv(out_csv, index=False, encoding="utf-8")
    #     print(f"Terminé — résultats sauvegardés dans {out_csv} ({len(df)} segments).")

if __name__ == "__main__":
    main()
