import json
import subprocess
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

# Direkte Suche nach "90 Sekunden"
SEARCH_QUERIES = [
    "ytsearch5:site:servustv.com Servus Nachrichten 90 Sekunden",
    "[servustv.com](https://www.servustv.com/aktuelles/v/)",  # Fallback: Nachrichten-Bereich
]


def run_ytdlp(url):
    """Führt yt-dlp aus und gibt Output zurück."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--flat-playlist",
        "--ignore-errors",
        url
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=120
        )
        return result.stdout.strip(), result.stderr
    except Exception as e:
        return "", str(e)


def search_servustv_direct():
    """Sucht direkt auf ServusTV nach der neuesten 90-Sekunden-Folge."""
    
    # Versuche verschiedene bekannte Video-IDs aus der Vergangenheit
    # um das URL-Pattern zu finden
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--ignore-errors",
        "--match-filter", "title~=(?i)90.sekunden",
        "[servustv.com](https://www.servustv.com/aktuelles/nachrichten/)"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    try:
                        return json.loads(line)
                    except:
                        continue
    except Exception as e:
        print(f"Fehler bei Direktsuche: {e}")
    
    return None


def search_via_webpage():
    """Fallback: Extrahiere Video-URLs von der Nachrichten-Seite."""
    import requests
    from bs4 import BeautifulSoup
    
    url = "[servustv.com](https://www.servustv.com/aktuelles/nachrichten/)"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Finde alle Video-Links
        links = soup.find_all("a", href=re.compile(r"/aktuelles/v/"))
        
        for link in links:
            href = link.get("href", "")
            text = link.get_text(" ", strip=True).lower()
            
            if "90 sekunden" in text or "90-sekunden" in text:
                full_url = href if href.startswith("http") else f"[servustv.com{href}](https://www.servustv.com{href})"
                
                # Hole Metadaten via yt-dlp
                output, _ = run_ytdlp(full_url)
                
                if output:
                    for line in output.split("\n"):
                        if line.strip():
                            try:
                                return json.loads(line)
                            except:
                                continue
    except Exception as e:
        print(f"Fehler bei Webpage-Suche: {e}")
    
    return None


def search_via_google():
    """Fallback: Nutze yt-dlp's Google-Suche."""
    
    output, stderr = run_ytdlp(
        "ytsearch3:servustv Servus Nachrichten in 90 Sekunden"
    )
    
    print(f"Google-Suche stderr: {stderr[:500] if stderr else 'none'}")
    
    if output:
        for line in output.split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                title = entry.get("title", "").lower()
                url = entry.get("webpage_url", "")
                
                if "servustv" in url and "90 sekunden" in title:
                    return entry
            except:
                continue
    
    return None


def extract_ticker(title):
    """Extrahiert Ticker-Topics aus dem Titel."""
    parts = [p.strip() for p in title.split("|")]
    
    topics = []
    for part in parts:
        if "90 sekunden" in part.lower():
            continue
        if part.lower().startswith("servus nachrichten") and len(part) < 35:
            continue
        if part:
            topics.append(part)
    
    return topics[:3] if topics else [title]


def main():
    old = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except:
            old = {}
    
    print("Suche neueste 90-Sekunden-Folge...")
    
    # Versuche verschiedene Methoden
    episode = None
    
    print("1. Versuche ServusTV direkt...")
    episode = search_servustv_direct()
    
    if not episode:
        print("2. Versuche Webpage-Scraping...")
        episode = search_via_webpage()
    
    if not episode:
        print("3. Versuche Google-Suche...")
        episode = search_via_google()
    
    if not episode:
        print("Keine Episode gefunden - behalte alte Daten")
        # Nicht abbrechen, sondern alte Daten behalten
        if "news90_link" in old:
            print(f"Behalte: {old.get('news90_title', 'unbekannt')}")
            return
        else:
            raise RuntimeError("Keine 90-Sekunden-Folge gefunden und keine alten Daten vorhanden.")
    
    title = episode.get("title", "Servus Nachrichten in 90 Sekunden")
    thumbnail = episode.get("thumbnail", "") or "news90.png"
    description = episode.get("description", "")
    webpage_url = episode.get("webpage_url", episode.get("url", ""))
    
    print(f"Gefunden: {title}")
    print(f"URL: {webpage_url}")
    
    topics = extract_ticker(title)
    ticker = " | ".join(topics)
    
    result = {
        "news90_title": title,
        "news90_link": webpage_url,
        "news90_url": webpage_url,
        "news90_image": thumbnail,
        "news90_thumbnail": thumbnail,
        
        "title": title,
        "short_title": title,
        "url": webpage_url,
        "image": thumbnail,
        
        "topics": topics,
        "ticker": ticker,
        "ticker90": ticker,
        "topmeldung90": ticker,
        
        "description": description
    }
    
    # Behalte andere Daten
    for key in ["google_headlines", "news1920_link", "news1920_image",
                "news1920_headlines", "news1920_title", "weather90_link",
                "weather90_image", "weather90_title"]:
        if key in old:
            result[key] = old[key]
    
    JSON_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print("\n✓ headlines.json aktualisiert")


if __name__ == "__main__":
    main()
