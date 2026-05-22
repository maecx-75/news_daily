import requests
from bs4 import BeautifulSoup
import json
import os
import re

def get_latest_news90():
    # Die von dir bereitgestellte Übersichtsseite für die 90-Sekunden-Nachrichten
    url = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        print(f"Lade Übersichtsseite: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Array für alle gefundenen Video-Links mit dem ServusTV-Muster
        video_links = []
        
        # Wir suchen nach allen Links, die eine Content-ID enthalten
        for a in soup.find_all('a', href=True):
            href = a['href']
            # ServusTV Video-IDs folgen meist dem Muster AA-XXXXXXXXXXXXX oder ähnlichen Hashes
            if "/de/page/AA-" in href or "/de/videos/aa-" in href.lower():
                # Verhindern, dass die Übersichtsseite selbst als "neues Video" genommen wird
                if "AA-1Y5RJCD1H2111" not in href:
                    video_links.append(href)
        
        if not video_links:
            print("Keine dynamischen Video-Links im HTML gefunden. Versuche Fallback über reguläre Ausdrücke...")
            # Fallback: Suche im gesamten Seitenquelltext nach Video-Pfaden (oft in JSON-Scripts auf der Seite)
            found_ids = re.findall(r'/de/[a-z]+/aa-[a-z0-9]+', response.text, re.IGNORECASE)
            for f_id in found_ids:
                if "AA-1Y5RJCD1H2111" not in f_id.upper():
                    video_links.append(f_id)

        if not video_links:
            print("Kritischer Fehler: Es konnte kein aktueller Video-Link extrahiert werden.")
            return

        # Da ServusTV die Videos chronologisch von links nach rechts listet,
        # ist das ERSTE gefundene Video im Quelltext die aktuellste Sendung.
        latest_path = video_links[0]
        
        # Absolute URL aufbauen
        if latest_path.startswith("/"):
            full_video_url = f"https://www.servustv.com{latest_path}"
        else:
            full_video_url = latest_path

        print(f"Erfolgreich aktuellste Sendung gefunden: {full_video_url}")

        # headlines.json laden oder neu erstellen
        json_path = "headlines.json"
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # Werte für das Frontend aktualisieren
        data["news90_link"] = full_video_url
        data["news90_title"] = "Servus Nachrichten in 90 Sekunden"
        # Standard-Hintergrundbild setzen, falls das Skript kein dynamisches Thumbnail parst
        data["news90_image"] = "https://s.servustv.com/v/img/news90_default.png" 

        # Datei sauber mit Einrückung zurückschreiben
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("headlines.json wurde erfolgreich aktualisiert.")

    except Exception as e:
        print(f"Fehler während der Ausführung des Skripts: {e}")

if __name__ == "__main__":
    get_latest_news90()
