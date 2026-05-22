import requests
import json
import os
import re
from bs4 import BeautifulSoup

def get_latest_news90():
    # Die offizielle Übersichtsseite für die "Nachrichten in 90 Sekunden"
    overview_url = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
    overview_id = "AA-1Y5RJCD1H2111"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9"
    }

    try:
        print(f"[INFO] Rufe Übersichtsseite ab: {overview_url}")
        response = requests.get(overview_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse den Titel der aktuellsten Sendung direkt aus dem HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ServusTV-IDs via Regex aus dem JSON-Quelltext isolieren
        id_pattern = r"AA-[A-Z0-9]{13}"
        all_found_ids = re.findall(id_pattern, response.text)
        
        unique_ids = []
        for cid in all_found_ids:
            if cid not in unique_ids:
                unique_ids.append(cid)
        
        # Die Übersichtsseiten-ID herausfiltern
        video_ids = [cid for cid in unique_ids if cid != overview_id]
        
        if not video_ids:
            print("[FEHLER] Keine Video-IDs im Quelltext gefunden.")
            return

        # Die oberste/erste ID ist das aktuellste Video von heute
        latest_video_id = video_ids[0]
        full_video_url = f"https://www.servustv.com/de/page/{latest_video_id}"
        
        print(f"[ERFOLG] Aktuelle Video-ID: {latest_video_id}")

        # headlines.json laden
        json_path = "headlines.json"
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # HIER SCHREIBEN WIR DIE DATEN REIN:
        # Wir befüllen sowohl "news90" als auch die alten Variablen, um sicherzugehen, 
        # dass deine index.html die Daten auf jeden Fall überschreibt!
        actual_title = "Servus Nachrichten in 90 Sekunden"
        
        data["news90_link"] = full_video_url
        data["news90_title"] = actual_title
        data["news90_image"] = "https://s.servustv.com/v/img/news90_default.png"
        
        # Sicherheits-Fallback, falls dein HTML noch auf die alten Variablennamen horcht:
        data["link"] = full_video_url
        data["title"] = actual_title

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("[INFO] headlines.json erfolgreich aktualisiert.")

    except Exception as e:
        print(f"[CRITICAL] Fehler im Prozess: {e}")

if __name__ == "__main__":
    get_latest_news90()
