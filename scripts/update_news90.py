import json
import requests

def fetch_latest_news90():
    print("Starte präzise API-Abfrage für 'Servus Nachrichten in 90 Sekunden'...")
    
    # Wir erhöhen das Limit auf 15, um genügend Auswahl zu haben, falls ältere Clips oben liegen
    api_url = "https://www.servustv.com/api/v1/contents/series/AA-1Z7U71WNW1W111/assets?limit=15&order=desc"
    
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
            
        latest_video = None
        
        # Signalsuche: Wir gehen die Liste von oben nach unten durch
        for item in assets:
            title = item.get("title", "")
            description = item.get("description", "")
            
            # Filter: Wenn 'Wegscheider' oder 'Wochenkommentar' im Titel vorkommt, überspringen wir das Video!
            if "wegscheider" in title.lower() or "wochenkommentar" in title.lower():
                print(f"Überspringe unerwünschten Inhalt: {title}")
                continue
                
            # Wir wollen nur Videos, die das Trennzeichen '|' enthalten (Anzeichen für die 3 Ticker-Themen)
            # ODER explizit ein News-Update sind
            if "|" in title or "nachrichten" in title.lower():
                latest_video = item
                break
        
        # Fallback: Falls gar kein Filter matcht, nehmen wir zähneknirschend das erste Element
        if not latest_video:
            print("Kein passendes News-Video per Filter gefunden. Nutze Fallback.")
            latest_video = assets[0]
            
        # 1. Link zusammenbauen
        relative_url = latest_video.get("url", "")
        video_link = f"https://www.servustv.com{relative_url}" if not relative_url.startswith("http") else relative_url
            
        # 2. Titel splitten für Kachel & Ticker
        raw_title = latest_video.get("title", "Servus Nachrichten in 90 Sekunden")
        print(f"Gewähltes Video: {raw_title}")
        
        themes = [t.strip() for t in raw_title.split("|") if t.strip()]
        
        if len(themes) >= 1:
            headline = themes[0]
        else:
            headline = "Servus Nachrichten in 90 Sekunden"
            
        while len(themes) < 3:
            themes.append(headline)
            
        ticker_text = f"{themes[0]} | {themes[1]} | {themes[2]}"
        
        # 3. Bildadresse ermitteln
        image_url = "news90.png"
        images = latest_video.get("images", {})
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
        print(f"Fehler bei API-Abfrage: {e}")
        return None

def merge_and_save(new_data):
    if not new_data:
        return
    try:
        with open("headlines.json", "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    except Exception:
        existing_data = {}
        
    existing_data.update(new_data)
    
    with open("headlines.json", "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    print("headlines.json erfolgreich aktualisiert!")

if __name__ == "__main__":
    news_data = fetch_latest_news90()
    merge_and_save(news_data)
