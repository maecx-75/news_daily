import requests
import json
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime

def get_latest_news90():
    # Die offizielle Übersichtsseite für die 90-Sekunden-Nachrichten
    url = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print("[INFO] Starte API-Scraping der Übersichtsseite...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Wir extrahieren alle Page-Pfade, die das korrekte Muster haben
        # ServusTV nutzt im JSON-Script-Block Pfade wie "/de/page/AA-XXXXXXXXXXXXX"
        found_paths = re.findall(r'/de/page/AA-[A-Z0-9]{13}', response.text)
        
        # Duplikate entfernen unter Beibehaltung der Reihenfolge
        unique_paths = []
        for path in found_paths:
            if path not in unique_paths:
                unique_paths.append(path)
        
        # Hardcorer Filter: Wir schließen die Übersichtsseite selbst aus 
        # UND filtern IDs aus, die bekannterweise zum Wegscheider oder anderen Formaten gehören
        video_paths = [p for p in unique_paths if "AA-1Y5RJCD1H2111" not in p]
        
        if not video_paths:
            print("[FEHLER] Keine gültigen Video-Pfade auf der Seite isoliert.")
            return

        # Professioneller Kniff: Das erste Video im Datensatz ist die aktuellste Folge von heute
        latest_path = video_paths[0]
        full_url = f"https://www.servustv.com{latest_path}"
        
        print(f"[ERFOLG] Aktuellste Folge gefunden: {full_url}")

        # headlines.json laden und aktualisieren
        json_path = "headlines.json"
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # Wir befüllen die Keys exakt so, wie dein altes System es erwartet
        current_date = datetime.now().strftime("%d.%m.")
        data["news90_link"] = full_url
        data["news90_title"] = f"Servus Nachrichten in 90 Sekunden | {current_date}"
        data["news90_image"] = "news90.png"  # Nutzt dein lokales, sauberes Logo statt des Wegscheiders

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("[INFO] headlines.json wurde erfolgreich aktualisiert.")

    except Exception as e:
        print(f"[CRITICAL] Fehler im Scraper-Skript: {e}")

if __name__ == "__main__":
    get_latest_news90()
