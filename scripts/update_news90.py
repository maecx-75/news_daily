import requests
import json
import os
import re
from datetime import datetime

def get_latest_news90():
    # Die offizielle Übersichtsseite für die 90-Sekunden-Nachrichten
    url = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print("[INFO] Starte Abruf der ServusTV-Nachrichten...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Isoliere alle Video-Pfad-IDs aus dem Quelltext
        found_paths = re.findall(r'/de/page/AA-[A-Z0-9]{13}', response.text)
        
        unique_paths = []
        for path in found_paths:
            if path not in unique_paths:
                unique_paths.append(path)
        
        # --- DER ENTSCHEIDENDE FILTER-FIX ---
        # Wir schließen die ID der Übersichtsseite aus UND blockieren explizit die ID des Wegscheiders (AAM4TZNNTHP15NYE8H3X)
        video_paths = [
            p for p in unique_paths 
            if "AA-1Y5RJCD1H2111" not in p and "AAM4TZNNTHP15NYE8H3X" not in p
        ]
        
        if not video_paths:
            print("[FEHLER] Keine echten Video-Links nach der Filterung übrig geblieben.")
            return

        # Nimm den ersten verbleibenden Link (das ist die echte aktuelle Nachrichtensendung)
        latest_path = video_paths[0]
        full_url = f"https://www.servustv.com{latest_path}"
        
        print(f"[ERFOLG] Echte Nachrichtensendung gefunden: {full_url}")

        # Pfad zur headlines.json im Hauptverzeichnis (Root) ermitteln
        json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "headlines.json"))

        # Bestehende JSON laden, um andere Keys (wie z.B. google_headlines) nicht zu löschen
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # Generiere dynamisch das aktuelle Datum für den Titel
        current_date = datetime.now().strftime("%d.%m.")
        aktueller_titel = f"Servus Nachrichten in 90 Sekunden | {current_date}"

        # Überschreibe NUR die relevanten Felder für die 90-Sekunden-Kachel
        data["title"] = aktueller_titel
        data["short_title"] = aktueller_titel
        data["full_title"] = aktueller_titel
        data["url"] = full_url
        data["href"] = full_url
        data["news90_title"] = aktueller_titel
        data["news90_link"] = full_url
        data["news90_image"] = "news90.png"  # Setzt dein sauberes, lokales Standard-Logo
        data["ticker"] = aktueller_titel
        data["ticker90"] = aktueller_titel
        data["topmeldung90"] = aktueller_titel
        data["description"] = "Die wichtigsten Nachrichten des Tages kompakt zusammengefasst."

        # Datei im Hauptverzeichnis speichern
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("[INFO] headlines.json wurde erfolgreich korrigiert und überschrieben.")

    except Exception as e:
        print(f"[CRITICAL] Fehler im Scraper-Prozess: {e}")

if __name__ == "__main__":
    get_latest_news90()
