import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

# Die Übersichtsseite, von der du die neuesten Folgen holst
PLAYLIST_URL = "[servustv.com](https://www.servustv.com/aktuelles/b/servus-nachrichten/aa-1y5rjcd1h2111/)"


def run_ytdlp(url, extra_args=None):
    """Führt yt-dlp aus und gibt JSON zurück."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--flat-playlist",
    ]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(url)
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.stdout.strip()


def find_90_sekunden_episode():
    """Sucht die neueste '90 Sekunden' Folge in der Playlist."""
    
    # Hole alle Einträge der Playlist
    output = run_ytdlp(PLAYLIST_URL)
    
    if not output:
        return None
    
    # Jede Zeile ist ein JSON-Objekt
    for line in output.split("\n"):
        if not line.strip():
            continue
        
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        title = entry.get("title", "").lower()
        
        # Suche nach "90 Sekunden" im Titel
        if "90 sekunden" in title:
            return entry
    
    return None


def get_full_metadata(url):
    """Holt vollständige Metadaten für ein einzelnes Video."""
    output = run_ytdlp(url, extra_args=["--no-flat-playlist"])
    
    if not output:
        return None
    
    # Bei einzelnen Videos: erste (und einzige) Zeile
    for line in output.split("\n"):
        if line.strip():
            return json.loads(line)
    
    return None


def extract_ticker(title):
    """Extrahiert Ticker-Topics aus dem Titel."""
    parts = [p.strip() for p in title.split("|")]
    
    topics = []
    for part in parts:
        # Überspringe den Serien-Titel
        if "90 sekunden" in part.lower():
            continue
        if part.lower().startswith("servus nachrichten") and len(part) < 35:
            continue
        if part:
            topics.append(part)
    
    return topics[:3] if topics else [title]


def main():
    # Lade bestehende Daten
    old = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            old = {}
    
    print("Suche neueste 90-Sekunden-Folge...")
    
    episode = find_90_sekunden_episode()
    
    if not episode:
        raise RuntimeError("Keine 90-Sekunden-Folge gefunden.")
    
    video_url = episode.get("url") or episode.get("webpage_url")
    
    print(f"Gefunden: {episode.get('title')}")
    print(f"URL: {video_url}")
    
    # Hole vollständige Metadaten
    meta = get_full_metadata(video_url)
    
    if not meta:
        meta = episode  # Fallback auf Playlist-Daten
    
    title = meta.get("title", "Servus Nachrichten in 90 Sekunden")
    thumbnail = meta.get("thumbnail", "news90.png")
    description = meta.get("description", "")
    webpage_url = meta.get("webpage_url", video_url)
    
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
    print(f"  Titel: {result['news90_title']}")
    print(f"  Link: {result['news90_link']}")
    print(f"  Ticker: {result['ticker']}")


if __name__ == "__main__":
    main()
