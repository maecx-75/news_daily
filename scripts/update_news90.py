import json
import re
from pathlib import Path
import requests

# Pfade definieren
ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

# Die direkte API-Schnittstelle von ServusTV für die Rubrik "Nachrichten"
API_URL = "https://www.servustv.com/api/v1/pages/de/page/AA-1Y5RJCD1H2111"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def fetch_latest_news90():
    print("Rufe Daten von der ServusTV API ab...")
    response = requests.get(API_URL, headers=HEADERS, timeout=30)
    
    if response.status_code != 200:
        raise RuntimeError(f"API-Abfrage fehlgeschlagen mit Statuscode: {response.status_code}")
        
    data = response.json()
    
    # Wir durchsuchen die API-Antwort nach Video-Kapiteln oder Kacheln
    # Die Struktur von ServusTV gruppiert die Videos oft in 'components' oder 'chapters'
    chapters = []
    
    # Rekursive Suche nach allen Video-Objekten in der API-Antwort
    def extract_videos(obj):
        if isinstance(obj, dict):
            if "title" in obj and "url" in obj:
                # Prüfen, ob es sich um die 90-Sekunden-Nachrichten handelt
                combined = f"{obj.get('title', '')} {obj.get('url', '')}".lower()
                if "90-sekunden" in combined or "90 sekunden" in combined:
                    chapters.append(obj)
            for value in obj.values():
                extract_videos(value)
        elif isinstance(obj, list):
            for item in obj:
                extract_videos(item)

    extract_videos(data)
    
    if not chapters:
        # Fallback: Wenn die spezifische ID leer ist, nutzen wir die allgemeine Nachrichten-Übersichts-API
        FALLBACK_URL = "https://www.servustv.com/api/v1/pages/de/page/AA89Q5GXCA4JIQJI54UM"
        response = requests.get(FALLBACK_URL, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            extract_videos(response.json())

    print(f"Gefundene API-Einträge für 90-Sekunden: {len(chapters)}")
    
    if not chapters:
        raise RuntimeError("Keine '90-Sekunden'-Beiträge in den API-Daten gefunden.")
        
    # Das aktuellste Video steht in der API standardmäßig ganz oben (Index 0)
    latest_video = chapters[0]
    return latest_video

def main():
    try:
        video_data = fetch_latest_news90()
    except Exception as e:
        print(f"Fehler beim Abrufen der API: {e}")
        return

    # Link formatieren (Sicherstellen, dass er absolut ist)
    url = video_data["url"]
    if url.startswith("/"):
        url = "https://www.servustv.com" + url

    title = video_data.get("title", "Servus Nachrichten in 90 Sekunden")
    
    # Bild-URL ermitteln (ServusTV nutzt oft verschachtelte Bildobjekte oder ein direktes 'image'-Feld)
    image_url = ""
    if "image" in video_data:
        if isinstance(video_data["image"], dict):
            image_url = video_data["image"].get("url", "")
        else:
            image_url = str(video_data["image"])
            
    desc = video_data.get("description", video_data.get("subTitle", "Der kompakte Nachrichten-Überblick direkt aus der News-Redaktion."))

    print("NEUESTE FOLGE GEFUNDEN:", title)
    print("LINK:", url)

    # Struktur für deine Webseite (exakt passend zu deinem alten Aufbau gebaut)
    result = {
        "title": title,
        "short_title": title,
        "full_title": title,

        "url": url,
        "href": url,

        "image": image_url,
        "thumbnail": image_url,

        "news90_title": title,
        "news90_link": url,
        "news90_image": image_url,
        "news90_thumbnail": image_url,

        "topics": [title],

        "ticker": title,
        "ticker90": title,
        "topmeldung90": title,

        "description": desc
    }

    # Alte Google-Headlines behalten, falls vorhanden
    old = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except:
            pass

    if "google_headlines" in old:
        result["google_headlines"] = old["google_headlines"]

    # Daten in headlines.json schreiben
    JSON_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("headlines.json ERFOLGREICH AKTUALISIERT!")


if __name__ == "__main__":
    main()
