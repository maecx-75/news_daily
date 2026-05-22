import json
import requests
import re

def fetch_latest_news90():
    print("Starte API-Abfrage für 'Servus Nachrichten in 90 Sekunden'...")
    
    # Der offizielle API-Endpunkt für die Video-Inhalte der Sendungsreihe
    api_url = "https://www.servustv.com/api/v1/contents/series/AA-1Z7U71WNW1W111/assets?limit=5&order=desc"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        assets = data.get("items", [])
        if not assets:
            print("Keine Videos in der API gefunden.")
            return None
            
        # Wir nehmen das oberste, also aktuellste Video
        latest_video = assets[0]
        
        # 1. Dynamischen Link extrahieren
        # ServusTV nutzt relative Pfade im Feld 'url', wir bauen den absoluten Link
        relative_url = latest_video.get("url", "")
        if not relative_url.startswith("http"):
            video_link = f"https://www.servustv.com{relative_url}"
        else:
            video_link = relative_url
            
        # 2. Titel analysieren und aufteilen
        # Beispiel-Titel von Servus: "Fahndung Österreich: Einbruch geklärt | Schwere Explosion in Erdölanlage | Höhere Strafen für Klima-Kleber?"
        raw_title = latest_video.get("title", "Servus Nachrichten in 90 Sekunden")
        print(f"Rohtitel aus API: {raw_title}")
        
        # Aufteilen am Trennzeichen '|'
        themes = [t.strip() for t in raw_title.split("|") if t.strip()]
        
        # Falls ServusTV das Format ändert, bauen wir Fallbacks auf
        if len(themes) >= 1:
            # Die erste Schlagzeile für die Kachel (z.B. "Fahndung Österreich": Einbruch geklärt)
            headline = themes[0]
        else:
            headline = "Aktuelle Meldungen"
            
        # Wenn weniger als 3 Themen da sind, füllen wir mit der Headline auf
        while len(themes) < 3:
            themes.append(headline)
            
        # Der Ticker oberhalb der Kachel bekommt genau das gewünschte Format mit " | " Trennung
        ticker_text = f"{themes[0]} | {themes[1]} | {themes[2]}"
        
        # 3. Thumbnail extrahieren
        image_url = "news90.png" # Fallback lokal
        images = latest_video.get("images", {})
        if images:
            # Wir suchen nach einem hochauflösenden Bild (z.B. Feld 'landscape' oder das erste verfügbare)
            for img_key in ['landscape', 'preview', 'fallback']:
                if img_key in images and images[img_key].get("url"):
                    image_url = images[img_key]["url"]
                    break
        
        return {
            "news90_link": video_link,
            "news90_title": headline,
            "ticker90": ticker_text,
            "news90_image": image_url
        }
        
    except Exception as e:
        print(f"Fehler beim Abfragen der Servus-API: {e}")
        return None

def merge_and_save(new_data):
    if not new_data:
        print("Keine neuen Daten zum Speichern vorhanden. Abbruch.")
        return
        
    # Bestandsdaten laden, um andere Kacheln (Wetter, Google) nicht zu überschreiben
    try:
        with open("headlines.json", "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    except Exception:
        existing_data = {}
        
    # Daten aktualisieren
    existing_data.update(new_data)
    
    # Zurückschreiben in die JSON-Datei
    with open("headlines.json", "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
    print("headlines.json erfolgreich aktualisiert!")
    print(f"Link: {existing_data.get('news90_link')}")
    print(f"Headline: {existing_data.get('news90_title')}")
    print(f"Ticker: {existing_data.get('ticker90')}")

if __name__ == "__main__":
    news_data = fetch_latest_news90()
    merge_and_save(news_data)
