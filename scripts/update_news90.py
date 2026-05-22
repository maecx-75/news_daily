import requests
import json
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime

def get_latest_news90():
    # Die ServusTV Übersichtsseite für die 90-Sekunden-Nachrichten
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
        
        # Regulärer Ausdruck für ServusTV Content-IDs (AA- gefolgt von 13 Zeichen)
        id_pattern = r"AA-[A-Z0-9]{13}"
        all_found_ids = re.findall(id_pattern, response.text)
        
        unique_ids = []
        for cid in all_found_ids:
            if cid not in unique_ids:
                unique_ids.append(cid)
        
        # Filtere die ID der Übersichtseite selbst heraus
        video_ids = [cid for cid in unique_ids if cid != overview_id]
        
        if not video_ids:
            print("[FEHLER] Keine Video-IDs im Quelltext gefunden.")
            return

        # Die allererste gefundene ID entspricht der neuesten Folge ganz links im Grid
        latest_video_id = video_ids[0]
        full_video_url = f"https://www.servustv.com/de/page/{latest_video_id}"
        
        print(f"[ERFOLG] Aktuelle Video-ID gefunden: {latest_video_id}")
        print(f"[INFO] Link generiert: {full_video_url}")

        # Aktuelles Datum für den Titel formatieren (z.B. "22.05.")
        current_date = datetime.now().strftime("%d.%m.")
        display_title = f"Servus Nachrichten in 90 Sekunden | {current_date}"

        # headlines.json laden oder neu anlegen
        json_path = "headlines.json"
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # Strukturierte Daten schreiben, die von der index.html ausgelesen werden
        data["news90_link"] = full_video_url
        data["news90_title"] = display_title
        data["news90_image"] = "https://s.servustv.com/v/img/news90_default.png"
        data["ticker90"] = f"+++ AKTUELL: {display_title} +++ Jetzt die neueste Sendung ansehen +++"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("[INFO] headlines.json erfolgreich mit neuen Daten überschrieben.")

    except Exception as e:
        print(f"[CRITICAL] Fehler im Scraper-Prozess: {e}")

if __name__ == "__main__":
    get_latest_news90()
