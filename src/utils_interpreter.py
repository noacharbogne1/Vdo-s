import re
import sqlite3

import config

def contains_video_protection(text):
    """
    Vérifie si le texte contient des mots-clés relatifs à la vidéo-protection.
    On teste plusieurs variantes (avec accent, sans accent, tiret).
    """
    if not text:
        return False
    keywords = ["vidéo-protection", "vidéoprotection", "video-protection", "video protection", "vidéo protection"]
    low = text.lower()
    return any(kw in low for kw in keywords)

def split_arretes(text):
    """
    Séparer plusieurs arrêtés contenus dans un même PDF.
    On cherche les titres fréquents (ex: "ARRÊTÉ", "Arrêté") en début de paragraphe.
    Retourne une liste de segments (chaque segment correspondant approximativement à un arrêté).
    """
    if not text:
        return []
    # pattern : split avant chaque occurrence d'un mot 'Arrêté' en début de ligne (avec ou sans majuscules/accent)
    parts = re.split(r"(?m)(?=\n?\s*(ARR[EÉ]T|Arr[EÉ]t[e]?\b))", text)
    # si split ne retourne pas de fragment utile, on renvoie le texte entier en une seule partie
    if len(parts) <= 1:
        return [text]
    # reconstruire les fragments correctement (les groupes capturés peuvent fragmenter)
    joined = []
    current = ""
    for p in parts:
        if re.match(r"(?m)^\s*(ARR[EÉ]T|Arr[EÉ]t[e]?\b)", p):
            # si current non vide, le pousser
            if current.strip():
                joined.append(current)
            current = p
        else:
            current += p
    if current.strip():
        joined.append(current)
    return joined

def interprete():
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    